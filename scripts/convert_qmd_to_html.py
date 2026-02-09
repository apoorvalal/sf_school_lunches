#!/usr/bin/env python3
"""
Convert Quarto markdown files to standalone HTML.
"""

import re
from pathlib import Path


def convert_qmd_to_html(qmd_path: Path, html_path: Path):
    """
    Simple converter from Quarto markdown to HTML.
    Handles basic markdown and inserts images with proper paths.
    """
    with open(qmd_path, "r") as f:
        content = f.read()
    
    # Remove YAML frontmatter if present
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            content = parts[2]
    
    # Convert markdown to HTML-friendly format
    html_lines = ["<!DOCTYPE html>", "<html>", "<head>"]
    html_lines.append('<meta charset="utf-8">')
    html_lines.append(f'<title>{qmd_path.stem}</title>')
    html_lines.append("""<style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; max-width: 900px; margin: 40px auto; padding: 20px; color: #333; }
        h1, h2, h3, h4 { color: #1f77b4; margin-top: 1.5em; }
        table { border-collapse: collapse; width: 100%; margin: 1em 0; }
        th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
        th { background-color: #f2f2f2; font-weight: bold; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        code { background-color: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-family: monospace; }
        pre { background-color: #f4f4f4; padding: 12px; border-radius: 5px; overflow-x: auto; }
        img { max-width: 100%; height: auto; margin: 20px 0; border-radius: 5px; }
        blockquote { border-left: 4px solid #1f77b4; margin: 1em 0; padding-left: 1em; color: #555; }
        a { color: #1f77b4; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>""")
    html_lines.append("</head>")
    html_lines.append("<body>")
    
    # Simple markdown to HTML conversion
    lines = content.split("\n")
    in_table = False
    
    for line in lines:
        # Skip empty lines after processing
        if not line.strip():
            if not in_table:
                html_lines.append("<p></p>")
            continue
        
        # Headings
        if line.startswith("##### "):
            html_lines.append(f"<h5>{line[6:].strip()}</h5>")
        elif line.startswith("#### "):
            html_lines.append(f"<h4>{line[5:].strip()}</h4>")
        elif line.startswith("### "):
            html_lines.append(f"<h3>{line[4:].strip()}</h3>")
        elif line.startswith("## "):
            html_lines.append(f"<h2>{line[3:].strip()}</h2>")
        elif line.startswith("# "):
            html_lines.append(f"<h1>{line[2:].strip()}</h1>")
        
        # Images
        elif line.strip().startswith("!["):
            match = re.search(r'!\[([^\]]*)\]\(([^\)]+)\)', line)
            if match:
                alt_text = match.group(1)
                img_path = match.group(2)
                html_lines.append(f'<img src="{img_path}" alt="{alt_text}" />')
        
        # Tables (pipe-delimited)
        elif "|" in line:
            in_table = True
            row = line.split("|")[1:-1]  # Remove leading/trailing empty
            row = [cell.strip() for cell in row]
            
            # Check if separator row (dashes and colons)
            if all(re.match(r'^[\-\:]+$', cell) for cell in row):
                continue
            
            if row:
                tag = "th" if not any("---" in cell for cell in row) else "td"
                html_lines.append("<table>")
                html_lines.append("<tr>")
                for cell in row:
                    # Remove markdown bold/italic
                    cell = cell.replace("**", "").replace("*", "").replace("_", "")
                    html_lines.append(f"<{tag}>{cell}</{tag}>")
                html_lines.append("</tr>")
        
        # Bold and italic
        else:
            text = line.strip()
            text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
            text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
            text = re.sub(r'__([^_]+)__', r'<strong>\1</strong>', text)
            text = re.sub(r'_([^_]+)_', r'<em>\1</em>', text)
            
            # Links
            text = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2">\1</a>', text)
            
            # Inline code
            text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
            
            if text:
                html_lines.append(f"<p>{text}</p>")
    
    html_lines.append("</body>")
    html_lines.append("</html>")
    
    html_path.parent.mkdir(parents=True, exist_ok=True)
    with open(html_path, "w") as f:
        f.write("\n".join(html_lines))
    
    print(f"Converted {qmd_path} → {html_path}")


def main():
    qmd_files = [
        Path("index.qmd"),
        Path("problem_formulation.qmd"),
        Path("report_sections/empirics_nested.qmd"),
    ]
    
    for qmd_file in qmd_files:
        if qmd_file.exists():
            html_file = qmd_file.with_suffix(".html")
            convert_qmd_to_html(qmd_file, html_file)
        else:
            print(f"⚠️  {qmd_file} not found")
    
    print("\n✅ HTML files generated in report root and report_sections/")


if __name__ == "__main__":
    main()
