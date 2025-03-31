from flask import Flask, render_template, request, send_file
import traceback
from io import BytesIO
import re
from bs4 import BeautifulSoup
import requests
import os

# 清除环境变量中的代理设置
if 'http_proxy' in os.environ:
    del os.environ['http_proxy']
if 'https_proxy' in os.environ:
    del os.environ['https_proxy']

app = Flask(__name__)

def sanitize_filename(filename):
    # 移除文件名中的非法字符
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

# 添加文本处理函数
def process_text(text):
    if not text:
        return text
    # 移除多余的空行，但保留段落之间的换行
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def get_article_content(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }
    
    session = requests.Session()
    session.trust_env = False
    
    response = session.get(url, headers=headers, timeout=10, proxies=None)
    response.raise_for_status()
    response.encoding = 'utf-8'
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 提取标题
    title = ''
    title_elem = soup.find('h1', id='activity-name') or \
                 soup.find('h1', class_='rich_media_title') or \
                 soup.find('h1')
    if title_elem:
        title = title_elem.get_text().strip()
    
    # 提取正文
    content = []
    seen_texts = set()  # 用于去重
    article_elem = soup.find('div', id='js_content')
    if article_elem:
        # 移除脚本、样式和不需要的元素
        for elem in article_elem(['script', 'style', 'link', 'iframe']):
            elem.decompose()
        
        # 移除作者信息和底部信息
        for elem in article_elem.find_all(['mpprofile', 'mp-profile', 'blockquote']):
            elem.decompose()
            
        # 需要过滤的关键词
        filter_starts = ['作者', '来源', '微信', '公众号', '关注', '点击', '来自', '编辑', 
                        '记者', '原创', '转载', '扫码', '二维码', '文/', '图/', '责编']
        
        # 按照DOM顺序处理所有元素
        for elem in article_elem.children:
            if elem.name in ['p', 'section', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'b']:
                # 获取元素中的所有文本
                text_parts = []
                for child in elem.stripped_strings:
                    text_parts.append(child)
                text = ' '.join(text_parts).strip()
                
                # 过滤和去重
                if text and text not in seen_texts:
                    # 检查是否包含需要过滤的关键词
                    should_skip = False
                    for keyword in filter_starts:
                        if text.startswith(keyword):
                            should_skip = True
                            break
                    
                    # 过滤掉太短的文本（可能是标签或者页面元素）
                    if len(text) < 2:
                        should_skip = True
                    
                    if not should_skip:
                        seen_texts.add(text)
                        content.append(text)
    
    # 使用双换行符连接段落
    content = '\n\n'.join(content)
    
    return title, content

@app.route('/', methods=['GET', 'POST'])
def index():
    content = ''
    title = ''
    error = None
    if request.method == 'POST':
        try:
            url = request.form['url']
            title, content = get_article_content(url)
            
            if not title:
                title = "未能提取标题"
            
            content = process_text(content)
            if not content:
                error = "无法提取文章内容，请确认链接是否正确"
                
        except Exception as e:
            error = f"提取失败: {str(e)}"
            print(traceback.format_exc())
    return render_template('index.html', content=content, title=title, error=error)

@app.route('/download', methods=['POST'])
def download():
    try:
        title = request.form.get('title', '未命名文章')
        content = request.form.get('content', '')
        
        # 确保标题不为空
        if not title.strip():
            title = '未命名文章'
            
        # 处理文件名
        filename = sanitize_filename(title) + '.txt'
        
        # 只使用正文内容，不包含标题
        file_content = content
        
        # 创建内存文件
        mem = BytesIO()
        mem.write(file_content.encode('utf-8'))
        mem.seek(0)
        
        return send_file(
            mem,
            as_attachment=True,
            download_name=filename,
            mimetype='text/plain'
        )
    except Exception as e:
        return str(e), 400

if __name__ == '__main__':
    app.run(debug=True) 