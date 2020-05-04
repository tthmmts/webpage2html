# Webpage2html

## Webpage2html: Save web page to a single html file

Original [webpage2html] script is developed by [zTrix].

This is a simple script to save a web page to a single html file, screenshot image file, link url list,.
No mhtml or pdf stuff, no xxx_files directory, just one single readable and editable html file.

The basic idea is to insert all css/javascript files into html directly, and use base64 data URI for image data.

## install

```bash
$ poetry install
```

## Usage and Example

Save web page directly

```bash
$ poetry run webpage2html https://www.google.com
```

## Dependency

This script require Python 3.7 or 3.8 with beautifulsoup4, lxml, fire, requests, selenium, chromedriver-binary packages and Google Chrome bwowser.

If you want to downlaod screenshots of Web page, you must get [Google Chrome version 81](https://www.google.com/intl/en/chrome/).

If you want to use arbitrary Chrome version, you update (or downgrade) chromedriver-binary package at your own risk.

```bash
$ poetry add chromedriver-binary@^83.0.0
```

I have tried the default `HTMLParser` and `html5lib` as the backend parser for BeautifulSoup, but both of them are buggy, `HTMLParser` handles self closing tags (like `<br>` `<meta>`) incorrectly(it will wait for closing tag for `<br>`, so If too many `<br>` tags exist in the html, BeautifulSoup will complain `RuntimeError: maximum recursion depth exceeded`), and `html5lib` will encode encoded html entities such as `&lt;` again to `&amp;lt;`, which is definitly unacceptable. I have tested many cases, and `lxml` works perfectly, so I choose to use `lxml` now.

## Unsupported Cases

### browser side less compiling

The page embeds less css directly and use less.js to compile in browser. In this case, I still cannot find a way to embed the less code into generated html to make it work.

```
<link rel="stylesheet/less" type="text/css" href="http://dghubble.com/blog/theme/css/style.less">
<script src="http://dghubble.com/blog/theme/js/less-1.5.0.min.js" type="text/javascript"></script>
```

- http://lesscss.org/#client-side-usage
- http://dghubble.com/blog/posts/.bashprofile-.profile-and-.bashrc-conventions/

### srcset attribute in img tag (html5)

Currently srcset is discarded.

# Contributors

1.  The original [webpage2html] script is developed by [zTrix]
1.  lukin.a.i submitted a patch to fix not recognised css link (rel=stylesheet) issue
1.  [Gruber](https://github.com/GlassGruber).
1.  Java port of this project. https://github.com/cedricblondeau/webpage2html-java
1.  [https://github.com/presto8](https://github.com/presto8)

# License

[webpage2html] use [SATA License](LICENSE.txt) (Star And Thank Author License), so you have to star this project before using. Read the [license](LICENSE.txt) carefully.

[webpage2html]: https://github.com/zTrix/webpage2html
[ztrix]: https://github.com/zTrix
