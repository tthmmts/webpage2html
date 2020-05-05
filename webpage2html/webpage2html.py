import base64
import datetime
import hashlib
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse, urlunsplit, urljoin, quote

import chromedriver_binary
import fire
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException

re_css_url = re.compile(r'(url\(.*?\))')
webpage2html_cache = {}


def log(s, new_line=True):
    """
    log を標準出力する
    """
    print(str(s), end=' ', file=sys.stderr)
    if new_line:
        sys.stderr.write('\n')
    sys.stderr.flush()


def prepare_download() -> str:
    """
    ダウンロードのディレクトリの準備
    """
    download_dir_name = 'download'
    download_dir_path = Path(download_dir_name)
    download_dir_path.mkdir(parents=True, exist_ok=True)

    download_dir_path_html = download_dir_path / "html"
    download_dir_path_html.mkdir(parents=True, exist_ok=True)
    download_dir_path_image = download_dir_path / "image"
    download_dir_path_image.mkdir(parents=True, exist_ok=True)
    download_dir_path_link = download_dir_path / "link"
    download_dir_path_link.mkdir(parents=True, exist_ok=True)

    download_dir_str = str(download_dir_path.resolve())
    return download_dir_str


def make_site_id(url: str = "") -> str:
    """
    ダウンロードのディレクトリの準備
    """
    result = hashlib.sha256(url.encode()).digest()
    # log(type(result))
    hash_str = base64.b32encode(result).decode("utf8")
    return hash_str


download_dir = prepare_download()
site_id = ""
external_links = []
internal_links = []
base_url = ""
user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:75.0) Gecko/20100101 Firefox/75.0"


def add_links(url: str = "") -> None:
    """
    リンクを外部と内部を分けて，リストにURLを追加する

    """
    global external_links
    global internal_links
    global base_url
    # log(f"{url} {base_url}")

    if url.lower().startswith('http'):
        if url.count("/") < 3 and base_url.startswith(url.split("?")[0]):
            internal_links.append(url)
        elif url.count("/") < 3:
            external_links.append(url)
        elif url.split("/")[2] == base_url.split("/")[2]:
            internal_links.append(url)
        else:
            external_links.append(url)


def absurl(index, relpath=None, normpath=None):
    if normpath is None:
        normpath = lambda x: x
    if index.lower().startswith('http') or (relpath and relpath.startswith('http')):
        new = urlparse(urljoin(index, relpath))
        return urlunsplit((new.scheme, new.netloc, normpath(new.path), new.query, ''))
    else:
        if relpath:
            return normpath(os.path.join(os.path.dirname(index), relpath))
        else:
            return index


def get_contents(url: str = None, relpath: str = None, verbose: bool = True, usecache: bool = True,
                 verify: bool = True, ignore_error: bool = False, username: str = None,
                 password: str = None, referer_url: str = ""):
    """
    Webコンテンツを取得する

    Args:
        url:
        relpath:
        verbose:
        usecache:
        verify:
        ignore_error:
        username:
        password:
        referer_url:

    Returns:

    """

    global webpage2html_cache
    global site_id
    global download_dir
    global user_agent

    if index.startswith('http') or (relpath and relpath.startswith('http')):
        full_path = absurl(index, relpath)
        if not full_path:
            if verbose:
                log(f'[ WARN ] invalid path, {index} {relpath}')
            return '', None
        # urllib2 only accepts valid url, the following code is taken from urllib
        # http://svn.python.org/view/python/trunk/Lib/urllib.py?r1=71780&r2=71779&pathrev=71780
        full_path = quote(full_path, safe="%/:=&?~#+!$,;'@()*[]")
        if usecache:
            if full_path in webpage2html_cache:
                if verbose:
                    log(f'[ CACHE HIT ] - {full_path}')
                return webpage2html_cache[full_path], None
        headers = {
            "accept": "image/webp,image/*,*/*;q=0.8",
            "accept-language": "ja,en-US;q=0.9,en;q=0.8",
            "user-agent": user_agent
        }
        if referer_url is not None and referer_url != "":
            headers.update({"referer": referer_url})

        auth = None
        if username and password:
            auth = requests.auth.HTTPBasicAuth(username, password)
        try:
            response = requests.get(full_path, headers=headers, verify=verify, auth=auth)
            if verbose:
                log('[ GET ] %d - %s' % (response.status_code, response.url))
            if not ignore_error and (response.status_code >= 400 or response.status_code < 200):
                content = ''
            elif response.headers.get('content-type', '').lower().startswith('text/'):
                content = response.text
            else:
                content = response.content
            if usecache:
                webpage2html_cache[response.url] = content
            return content, {'url': response.url,
                             'content-type': response.headers.get('content-type')}
        except Exception as ex:
            if verbose:
                log(f'[ WARN ] ??? - {full_path}: {ex}')
            return '', None
    elif os.path.exists(index):
        if relpath:
            relpath = relpath.split('#')[0].split('?')[0]
            if os.path.exists(relpath):
                full_path = relpath
            else:
                full_path = os.path.normpath(os.path.join(os.path.dirname(index), relpath))
            try:
                ret = open(full_path, 'rb').read()
                if verbose:
                    log(f'[ LOCAL ] found - {full_path}')
                return ret, None
            except IOError as ex:
                if verbose:
                    msg = str(ex)
                    log(f'[ WARN ] file not found - {full_path} {msg}')
                return '', None
        else:
            try:
                ret = open(index, 'rb').read()
                if verbose:
                    log(f'[ LOCAL ] found - {index}')
                return ret, None
            except IOError as err:
                if verbose:
                    msg = str(err)
                    log(f'[ WARN ] file not found - {index} {msg}')
                return '', None
    else:
        if verbose:
            log(f'[ ERROR ] invalid index - {index}')
        return '', None


def get_contents_by_selenium(url: str = None,
                             relpath: str = None,
                             verbose: bool = True,
                             usecache: bool = True,
                             verify: bool = True,
                             ignore_error: bool = False,
                             username: str = None,
                             password: str = None,
                             flg_screen_shot: bool = False,
                             referer_url: str = ""
                             ) -> tuple:
    """
    Selenium を利用して，Webコンテンツを取得する

    Args:
        url:
        relpath:
        verbose:
        usecache:
        verify:
        ignore_error:
        username:
        password:
        flg_screen_shot:
        referer_url:

    Returns:

    """

    global site_id
    global download_dir
    global webpage2html_cache
    global user_agent

    url = absurl(url, base_url)
    full_path = quote(url, safe="%/:=&?~#+!$,;'@()*[]")
    if usecache:
        if full_path in webpage2html_cache:
            if verbose:
                log(f'[ CACHE HIT ] - {full_path}')
            return webpage2html_cache[full_path], {'url': url, 'content-type': "text/html"}

    if not url.startswith("http"):
        if usecache:
            contents = "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'><title>No title</title></head><body><!-- No content --></body></html>"
            webpage2html_cache[full_path] = contents
            return contents, {'url': url, 'content-type': "text/html"}

    log(f"[ DEBUG ] - Get by selenium: {url} as {site_id}")
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument("--incognito")
    options.add_argument("--hide-scrollbars")
    options.add_argument("--test-type")

    if not chromedriver_binary:
        return get_contents(url, referer_url=referer_url)
    try:
        with webdriver.Chrome(options=options) as driver:
            try:
                user_agent = driver.execute_script("return navigator.userAgent;")
                driver.set_window_size(1920, 1080)
                driver.get(url)
                if flg_screen_shot:
                    width = driver.execute_script("return document.body.clientWidth;")
                    driver.set_window_size(max(width, 1920), 1080)
                    time.sleep(2)
                    height = driver.execute_script("""
                        var maxHeight = document.body.clientHeight;
                        var childrenNodes = document.body.children;
                        for (const num in childrenNodes) {
                          if (! isNaN(childrenNodes[num].clientHeight)){
                            if (childrenNodes[num].clientHeight >maxHeight)
                              {maxHeight = childrenNodes[num].clientHeight;}
                            }
                        };
                        return maxHeight;""")
                    # log(height)
                    driver.set_window_size(max(width, 1920), max(height, 1080))
                    time.sleep(2)
                    driver.execute_script(f"window.scrollTo(0, {height})")
                    time.sleep(12)
                    driver.execute_script("window.scrollTo(0, 0)")
                    time.sleep(2)
                    html_text = driver.page_source
                    driver.save_screenshot(f'{download_dir}/image/{site_id}.png')
            except TimeoutException as ex:
                log(f"[ERROR]\tTimeoutException: '{ex}'")
                html_text = "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'><title>No title</title></head><body><!-- No content --></body></html>"
            else:
                driver.quit()
    except Exception as ex:
        log(f"[ERROR]\twebdriver Chrome: '{ex}'")
        log(f"[WARN]\tGet web page by request without screenshot")
        return get_contents(url, referer_url=referer_url)

    if usecache:
        webpage2html_cache[full_path] = html_text

    return html_text, {'url': url, 'content-type': "text/html"}


def data_to_base64(index, src, verbose: bool = True, referer_url: str = None):
    # doc here: http://en.wikipedia.org/wiki/Data_URI_scheme
    sp = urlparse(src).path.lower()
    if src.strip().startswith('data:'):
        return src
    elif src.strip().startswith('javascript:'):
        return src

    if sp.endswith('.png'):
        fmt = 'image/png'
    elif sp.endswith('.gif'):
        fmt = 'image/gif'
    elif sp.endswith('.ico'):
        fmt = 'image/x-icon'
    elif sp.endswith('.jpg') or sp.endswith('.jpeg'):
        fmt = 'image/jpeg'
    elif sp.endswith('.webp'):
        fmt = 'image/webp'
    elif sp.endswith('.svg'):
        fmt = 'image/svg+xml'
    elif sp.endswith('.ttf'):
        fmt = 'application/x-font-ttf'
    elif sp.endswith('.otf'):
        fmt = 'application/x-font-opentype'
    elif sp.endswith('.woff'):
        fmt = 'application/font-woff'
    elif sp.endswith('.woff2'):
        fmt = 'application/font-woff2'
    elif sp.endswith('.eot'):
        fmt = 'application/vnd.ms-fontobject'
    elif sp.endswith('.sfnt'):
        fmt = 'application/font-sfnt'
    elif sp.endswith('.css') or sp.endswith('.less') or src.startswith("https://fonts.googleapis.com/css"):
        fmt = 'text/css'
    elif sp.endswith('.js'):
        fmt = 'application/javascript'
    elif sp.endswith(".html") or sp.endswith(".htm"):
        fmt = "text/html"
    elif sp.endswith(".txt") or sp.endswith(".md"):
        fmt = "text/text"
    elif sp.endswith(".json"):
        fmt = "application/json"
    else:
        fmt = 'image/png'

    # html ファイルの場合 Selenium を利用して取得する．それ以外は，referer をつけて Requestsを利用する．
    if fmt == "text/html":
        data, extra_data = get_contents_by_selenium(index, src)
    else:
        # log(f"{index} , {sp} <- {src} as {fmt}")
        data, extra_data = get_contents(index, src, verbose=verbose, referer_url=referer_url)

    if extra_data and extra_data.get('content-type'):
        fmt = extra_data.get('content-type').strip().replace(' ', '')

    if fmt == "image/jpg":
        fmt = "image/jpeg"
    if data:
        # log(f"{index}, {fmt}, {type(data)}")
        if isinstance(data, bytes):
            # return f'data:{fmt};base64,' + bytes.decode(base64.b64encode(data))
            return f'data:{fmt};base64,{base64.b64encode(data).decode("utf-8")}'
        else:
            return f'data:{fmt};base64,{base64.b64encode(str.encode(data)).decode("utf-8")}'
    else:
        return absurl(index, src)


css_encoding_re = re.compile(r'''@charset\s+["']([-_a-zA-Z0-9]+)["'];''', re.I)


def handle_css_content(index, css, verbose=True, referer_url: str = None):
    if not css:
        return css
    if not isinstance(css, str):
        css = bytes.decode(css)
        mo = css_encoding_re.search(css)
        if mo:
            try:
                css = css.decode(mo.group(1))
            except Exception as ex:
                log(f'[WARN]\tfailed to convert css to encoding {mo.group(1)}: {ex}')
    # Watch out! how to handle urls which contain parentheses inside? Oh god, css does not support such kind of urls
    # I tested such url in css, and, unfortunately, the css rule is broken. LOL!
    # I have to say that, CSS is awesome!
    reg = re.compile(r'url\s*\((.+?)\)')

    def repl(matchobj) -> str:
        src = matchobj.group(1).strip(' \'"')
        # if src.lower().endswith('woff') or src.lower().endswith('ttf') or src.lower().endswith('otf') or src.lower().endswith('eot'):
        #     # dont handle font data uri currently
        #     return 'url(' + src + ')'
        base64_str = data_to_base64(index, src, verbose=verbose, referer_url=referer_url)
        return f'url("{base64_str}")'

    css = reg.sub(repl, css)
    return css


def generate(url,
             verbose=True,
             comment=True,
             keep_script=False,
             prettify=False,
             full_url=True,
             verify=True,
             errorpage=False,
             username=None, password=None,
             level: int = 1,
             **kwargs):
    """
    given a index url such as http://www.google.com, http://custom.domain/index.html
    return generated single html
    """

    global site_id
    global base_url

    if level <= 1:
        base_url = url
        site_id = make_site_id(url)

    # html_doc, extra_data = get(index, verbose=verbose, verify=verify, ignore_error=errorpage,
    #                            username=username, password=password)
    #
    # if extra_data and extra_data.get('url'):
    #     index = extra_data['url']

    html_doc, _ = get_contents_by_selenium(url, flg_screen_shot=True)
    referer_url = url

    # now build the dom tree
    # soup = BeautifulSoup(html_doc, 'lxml')
    soup = BeautifulSoup(html_doc, 'html5lib')
    soup_title = soup.title.string if soup.title else ''
    log(f"[ INFO ] get {soup_title}")

    for link in soup('link'):
        if link.get('href'):
            # add_links(absurl(url, link['href']))
            if 'mask-icon' in (link.get('rel') or []) or 'icon' in (link.get('rel') or []) or 'apple-touch-icon' in (
                    link.get('rel') or []) or 'apple-touch-icon-precomposed' in (link.get('rel') or []):
                link['data-href'] = link['href']
                link['href'] = data_to_base64(url, link['href'], verbose=verbose)
            elif link.get('type') == 'text/css' or \
                    link['href'].lower().endswith('.css') or \
                    'stylesheet' in (link.get('rel') or []):
                new_type = 'text/css' if not link.get('type') else link['type']
                css = soup.new_tag('style', type=new_type)
                css['data-href'] = link['href']
                for attr in link.attrs:
                    if attr in ['href']:
                        continue
                    css[attr] = link[attr]

                css_data, _ = get_contents(url,
                                           relpath=link['href'],
                                           verbose=verbose,
                                           referer_url=referer_url)

                new_css_content = handle_css_content(absurl(url, link['href']),
                                                     css_data,
                                                     verbose=verbose,
                                                     referer_url=referer_url)
                # if "stylesheet/less" in '\n'.join(link.get('rel') or []).lower():
                # fix browser side less: http://lesscss.org/#client-side-usage
                #     # link['href'] = 'data:text/less;base64,' + base64.b64encode(css_data)
                #     link['data-href'] = link['href']
                #     link['href'] = absurl(index, link['href'])
                if False:  # new_css_content.find('@font-face') > -1 or new_css_content.find('@FONT-FACE') > -1:
                    link['href'] = 'data:text/css;base64,' + base64.b64encode(new_css_content)
                else:
                    css.string = new_css_content
                    link.replace_with(css)
            elif full_url:
                link['data-href'] = link['href']
                link['href'] = absurl(url, link['href'])

    # Javascript を抜き出す
    for js in soup('script'):
        if not keep_script:
            js.replace_with('')
            continue
        if not js.get('src'):
            continue
        new_type = 'text/javascript' if not js.has_attr('type') or not js['type'] else js['type']
        code = soup.new_tag('script', type=new_type)
        code['data-src'] = js['src']
        js_str, _ = get_contents(url, relpath=js['src'], verbose=verbose, referer_url=referer_url)
        if type(js_str) == bytes:
            js_str = js_str.decode('utf-8')
        try:
            if js_str.find('</script>') > -1:
                code['src'] = 'data:text/javascript;base64,' + base64.b64encode(js_str.encode()).decode()
            elif js_str.find(']]>') < 0:
                code.string = '<!--//--><![CDATA[//><!--\n' + js_str + '\n//--><!]]>'
            else:
                # replace ]]> does not work at all for chrome, do not believe
                # http://en.wikipedia.org/wiki/CDATA
                # code.string = '<![CDATA[\n' + js_str.replace(']]>', ']]]]><![CDATA[>') + '\n]]>'
                code.string = js_str
        except Exception as ex:
            if verbose:
                log(f"[ERROR]\t{repr(js_str)}: {ex}")
            raise
        js.replace_with(code)

    # iframe の内容を取得
    for i_frame in soup("iframe"):
        if i_frame.get('src'):
            log(f"[ DEBUG ] found iframe {i_frame['src']}")
            # log(absurl(url, i_frame['src']))
            i_frame['data-src'] = i_frame['src']
            if level <= 1:
                i_frame_html = generate(i_frame['src'], level=level + 1, referer_url=referer_url)
                add_links(absurl(url, i_frame['data-src']))
            else:
                i_frame_html = "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'><title>Grandchild title</title></head><body><!-- Grandchild content --></body></html>"
            i_frame['src'] = 'data:text/html;base64,' + base64.b64encode(i_frame_html.encode()).decode()

    # iframe の内容を取得
    for frame in soup("frame"):
        if frame.get('src'):
            log(f"[ DEBUG ] found frames {frame['src']}")
            frame['data-src'] = frame['src']
            if level <= 1:
                frame_html = generate(frame['src'], level=level + 1, referer_url=referer_url)
                add_links(absurl(url, frame['data-src']))
            else:
                frame_html = "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'><title>Grandchild title</title></head><body><!-- Grandchild content --></body></html>"
            frame['src'] = 'data:text/html;base64,' + base64.b64encode(frame_html.encode()).decode()
    for img in soup('img'):
        if not img.get('src'):
            continue
        img['data-src'] = img['src']
        img['src'] = data_to_base64(url, img['src'], verbose=verbose)

        # `img` elements may have `srcset` attributes with multiple sets of images.
        # To get a lighter document it will be cleared, and used only the standard `src` attribute
        # Maybe add a flag to enable the base64 conversion of each `srcset`?
        # For now a simple warning is displayed informing that image has multiple sources
        # that are stripped.

        if img.get('srcset'):
            img['data-srcset'] = img['srcset']
            del img['srcset']
            if verbose:
                log(f"[ WARN ] srcset found in img tag. Attribute will be cleared. File src => {img['data-src']}")

        def check_alt(attr):
            if img.has_attr(attr) and img[attr].startswith('this.src='):
                # we do not handle this situation yet, just warn the user
                if verbose:
                    log(f'[ WARN ] {attr} found in img tag and unhandled, which may break page')

        check_alt('onerror')
        check_alt('onmouseover')
        check_alt('onmouseout')

    for tag in soup(True):
        # HTMLの文字コードにUTF-8を設定する
        if tag.name == "meta" and tag.has_attr('charset') and tag['charset'].lower() != "uft-8":
            tag["charset"] = "UTF-8"
        elif tag.name == "meta" and tag.has_attr('http-equiv') and tag['http-equiv'].lower() == "content-type" \
                and tag.has_attr('content'):
            tag["content"] = "text/html; charset=UTF-8"
        if full_url and tag.name == 'a' and tag.has_attr('href') and not tag['href'].startswith('#'):
            tag['data-href'] = tag['href']
            tag['href'] = absurl(url, tag['href'])
            add_links(tag['href'])
        if tag.has_attr('style'):
            if tag['style']:
                tag['style'] = handle_css_content(url, tag['style'], verbose=verbose)
        elif tag.name == 'link' and tag.has_attr('type') and tag['type'] == 'text/css':
            if tag.string:
                tag.string = handle_css_content(url, tag.string, verbose=verbose)
        elif tag.name == 'style':
            if tag.string:
                tag.string = handle_css_content(url, tag.string, verbose=verbose)

    if level > 1:
        return soup.prettify(formatter='html5')

    html_file_path = f"{download_dir}/html/{site_id}.html"

    result = soup.prettify(formatter='html5').replace("url(data:image/jpg;base64,", "url(data:image/jpeg;base64,")
    result = re.sub(r'url\s*\((data:.+?)\)', r'url("\1")', result)

    with open(html_file_path, 'w') as f:
        # f.write(str(soup))
        f.write(result)

    save_links()
    save_url_id_list()
    # if prettify:
    #     return soup.prettify(formatter='html')
    # else:
    #     return str(soup)


def save_links():
    global external_links
    global internal_links
    global base_url

    links = [base_url]
    internal_links.sort()
    for url in sorted(set(internal_links)):
        if url not in links:
            links.append(url)
    for url in sorted(set(external_links)):
        if url not in links:
            links.append(url)

    link_file_path = f"{download_dir}/link/{site_id}.txt"
    with open(link_file_path, 'w') as f:
        f.write("\n".join(links))


def save_url_id_list():
    global site_id
    global base_url
    link_file_path = f"{download_dir}/url_id_list.txt"
    date = datetime.datetime.today().isoformat().split('.')[0].replace("T", " ")
    text = f"{site_id}\t{base_url}\t{date}\n"
    with open(link_file_path, 'a') as f:
        f.write(text)


#
# def usage():
#     print("""
# usage:
#
#     $ poetry run webpage2html URL
#
# examples:
#     $ poetry run webpage2html http://www.google.com
#     $ poetry run webpage2html http://gabrielecirulli.github.io/2048/
# """)
#
#
# def main(kwargs):
#     kwargs = {}
#     parser = argparse.ArgumentParser()
#     parser.add_argument('-q', '--quiet', action='store_true', help="don't show verbose url get log in stderr")
#     parser.add_argument("url", help="the website to store")
#     args = parser.parse_args()
#
#     args.verbose = not args.quiet
#     args.keep_script = args.script
#     args.verify = not args.insecure
#     args.index = args.url
#     kwargs = vars(args)
#
#     rs = generate(**kwargs)
#     if args.output and args.output != '-':
#         with open(args.output, 'wb') as f:
#             f.write(rs.encode())
#     else:
#         sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
#         sys.stdout.write(rs)

def short_cut(url):
    generate(url)


def main():
    fire.Fire(short_cut)


if __name__ == "__main__":
    main()
