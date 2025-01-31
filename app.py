from flask import Flask, render_template, request, send_file
import newspaper
from newspaper import Article
import traceback
from io import BytesIO
import re
from bs4 import BeautifulSoup
import nltk

# 下载必要的nltk数据
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

app = Flask(__name__)

def sanitize_filename(filename):
    # 移除文件名中的非法字符
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

# 添加文本处理函数
def process_text(text):
    if not text:
        return text
    # 将多个连续换行替换为单个换行
    text = re.sub(r'\n\s*\n', '\n', text)
    # 去除开头和结尾的空白
    return text.strip()

@app.route('/', methods=['GET', 'POST'])
def index():
    content = ''
    title = ''
    error = None
    if request.method == 'POST':
        try:
            url = request.form['url']
            article = Article(url, language='zh')
            # 设置用户代理，减少被反爬概率
            article.config.browser_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            article.download()
            article.parse()
            
            # 尝试提取标题
            title = article.title
            if not title:
                # 如果标题为空，尝试从HTML中直接提取
                soup = BeautifulSoup(article.html, 'html.parser')
                # 微信文章标题通常在这些元素中
                title_elem = soup.find('h1', id='activity-name') or \
                           soup.find('h1', class_='rich_media_title') or \
                           soup.find('h1')
                if title_elem:
                    title = title_elem.get_text().strip()
            
            # 如果还是没有标题，设置默认值
            if not title:
                title = "未能提取标题"
            else:
                title = title.strip()
            
            # 处理正文
            content = process_text(article.text)
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

@app.route('/health')
def health_check():
    return 'OK', 200

# 修改运行配置
if __name__ == '__main__':
    # 本地开发时使用
    app.run(debug=True)
else:
    # Vercel 部署时使用
    app.debug = False 