#!/usr/bin/env python3
"""
WordPress XML to Markdown Converter

Extracts posts from WordPress XML export files and converts them to Markdown format.
"""

import xml.etree.ElementTree as ET
import html
import re
from pathlib import Path
from datetime import datetime
import json

def parse_wordpress_xml(xml_file):
    """Parse WordPress XML export file and extract posts."""
    
    # Parse the XML file
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    # Define namespaces
    namespaces = {
        'content': 'http://purl.org/rss/1.0/modules/content/',
        'wp': 'http://wordpress.org/export/1.2/',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'excerpt': 'http://wordpress.org/export/1.2/excerpt/'
    }
    
    # Find all items (posts, pages, attachments)
    items = root.findall('.//item')
    
    posts = []
    
    for item in items:
        # Extract post type
        post_type_elem = item.find('wp:post_type', namespaces)
        if post_type_elem is None:
            continue
            
        post_type = post_type_elem.text
        
        # Skip non-post items (attachments, navigation menus, etc.)
        if post_type not in ['post', 'page']:
            continue
            
        # Extract post data
        post = {}
        
        # Basic fields
        post['title'] = item.find('title').text or ''
        post['title'] = html.unescape(post['title'])
        
        post['link'] = item.find('link').text or ''
        post['pub_date'] = item.find('pubDate').text or ''
        
        # Parse date to a more readable format
        if post['pub_date']:
            try:
                dt = datetime.strptime(post['pub_date'], '%a, %d %b %Y %H:%M:%S %z')
                post['date'] = dt.strftime('%Y-%m-%d')
                post['datetime'] = dt.isoformat()
            except:
                post['date'] = post['pub_date']
                post['datetime'] = post['pub_date']
        
        # Content
        content_elem = item.find('content:encoded', namespaces)
        post['content'] = content_elem.text if content_elem is not None else ''
        
        # Excerpt
        excerpt_elem = item.find('excerpt:encoded', namespaces)
        post['excerpt'] = excerpt_elem.text if excerpt_elem is not None else ''
        
        # WordPress specific fields
        post['post_id'] = item.find('wp:post_id', namespaces).text
        post['post_name'] = item.find('wp:post_name', namespaces).text or ''
        post['status'] = item.find('wp:status', namespaces).text or 'draft'
        
        # Categories and tags
        categories = []
        tags = []
        
        for cat in item.findall('category'):
            domain = cat.get('domain', '')
            nicename = cat.get('nicename', '')
            text = cat.text or ''
            
            if domain == 'category':
                categories.append(html.unescape(text))
            elif domain == 'post_tag':
                tags.append(html.unescape(text))
        
        post['categories'] = categories
        post['tags'] = tags
        
        # Author
        creator_elem = item.find('dc:creator', namespaces)
        post['author'] = creator_elem.text if creator_elem is not None else ''
        
        # Only add published posts (or include drafts if needed)
        if post['status'] == 'publish':
            posts.append(post)
    
    return posts

def convert_wordpress_blocks_to_markdown(content):
    """Convert WordPress block editor content to Markdown."""
    
    if not content:
        return ''
    
    # Decode HTML entities
    content = html.unescape(content)
    
    # WordPress block comments patterns
    patterns = [
        # Remove WordPress block comments
        (r'<!-- wp:[\w\-/]+(.*?)-->', ''),
        (r'<!-- /wp:[\w\-/]+ -->', ''),
        
        # Convert headings
        (r'<h1[^>]*>(.*?)</h1>', r'# \1'),
        (r'<h2[^>]*>(.*?)</h2>', r'## \1'),
        (r'<h3[^>]*>(.*?)</h3>', r'### \1'),
        (r'<h4[^>]*>(.*?)</h4>', r'#### \1'),
        (r'<h5[^>]*>(.*?)</h5>', r'##### \1'),
        (r'<h6[^>]*>(.*?)</h6>', r'###### \1'),
        
        # Convert paragraphs
        (r'<p[^>]*>(.*?)</p>', r'\1\n'),
        
        # Convert strong and emphasis
        (r'<strong[^>]*>(.*?)</strong>', r'**\1**'),
        (r'<b[^>]*>(.*?)</b>', r'**\1**'),
        (r'<em[^>]*>(.*?)</em>', r'*\1*'),
        (r'<i[^>]*>(.*?)</i>', r'*\1*'),
        
        # Convert links
        (r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)'),
        
        # Convert lists
        (r'<ul[^>]*>', ''),
        (r'</ul>', '\n'),
        (r'<ol[^>]*>', ''),
        (r'</ol>', '\n'),
        (r'<li[^>]*>(.*?)</li>', r'- \1'),
        
        # Convert blockquotes
        (r'<blockquote[^>]*>(.*?)</blockquote>', r'> \1'),
        
        # Convert code
        (r'<code[^>]*>(.*?)</code>', r'`\1`'),
        (r'<pre[^>]*>(.*?)</pre>', r'```\n\1\n```'),
        
        # Convert images
        (r'<img[^>]*src="([^"]*)"[^>]*alt="([^"]*)"[^>]*/>', r'![\2](\1)'),
        (r'<img[^>]*src="([^"]*)"[^>]*/>', r'![](\1)'),
        
        # Convert figure/figcaption
        (r'<figure[^>]*>(.*?)</figure>', r'\1'),
        (r'<figcaption[^>]*>(.*?)</figcaption>', r'\n*\1*\n'),
        
        # Convert horizontal rules
        (r'<hr[^>]*/>', '---'),
        
        # Convert line breaks
        (r'<br[^>]*/>', '\n'),
        
        # Remove divs and spans
        (r'<div[^>]*>', ''),
        (r'</div>', ''),
        (r'<span[^>]*>', ''),
        (r'</span>', ''),
        
        # Remove remaining HTML tags not explicitly handled
        (r'<[^>]+>', ''),
    ]
    
    # Apply all patterns
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content, flags=re.DOTALL | re.MULTILINE)
    
    # Clean up extra whitespace
    content = re.sub(r'\n{3,}', '\n\n', content)
    content = content.strip()
    
    return content

def create_markdown_file(post, output_dir):
    """Create a text file with just the post content."""
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create filename from post title or slug
    if post['post_name']:
        filename = post['post_name']
    else:
        filename = re.sub(r'[^\w\s-]', '', post['title'].lower())
        filename = re.sub(r'[-\s]+', '-', filename)
    
    # Limit filename length
    if len(filename) > 100:
        filename = filename[:100]
    
    # Add date prefix if available
    if post.get('date'):
        filename = f"{post['date']}-{filename}"
    
    filename = f"{filename}.txt"
    filepath = output_dir / filename
    
    # Convert content to plain text (remove HTML and WordPress blocks)
    plain_text = convert_wordpress_blocks_to_markdown(post['content'])
    
    # Write just the content
    filepath.write_text(plain_text, encoding='utf-8')
    
    return filepath

def main():
    """Main function to convert WordPress XML to plain text."""
    
    # Configuration
    xml_file = '../gdrive/burningman/indiedocjourney.wordpress.com-2025-02-05-02_44_39-sr1sgysdvap5fb1gzupgwat2dlinsqiy/indiedocjourney.wordpress.com-2025-02-05-02_44_36/lightscamerajourneycapturinguntoldstories.wordpress.2025-02-05.000.xml'
    output_dir = 'wordpress_posts_text'
    
    print(f"📖 Parsing WordPress XML file: {xml_file}")
    
    try:
        # Parse XML and extract posts
        posts = parse_wordpress_xml(xml_file)
        print(f"✅ Found {len(posts)} published posts")
        
        # Convert each post to plain text
        print(f"\n📝 Converting posts to plain text...")
        for i, post in enumerate(posts, 1):
            filepath = create_markdown_file(post, output_dir)
            print(f"  [{i}/{len(posts)}] Created: {filepath.name}")
        
        print(f"\n✨ Successfully converted {len(posts)} posts to plain text!")
        print(f"📁 Output directory: {output_dir}/")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())