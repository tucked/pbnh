pbnh
========
[pbnh](https://github.com/bhanderson/pbnh) is our implementation of a pastebin server using flask and postgres or sqlite

It is highly derived from [silverp1's](https://github.com/silverp1) and [buhman's](https://github.com/buhman) project [pb](https://github.com/ptpb/pb) and they deserve the recognition for this idea.

The syntax highlighting is done using [codemirrors](https://github.com/codemirror/codemirror) javascript library.

The icons are from [Font Awesome](https://fortawesome.github.io/Font-Awesome/)

## Table of Contents
 * [pbnh](#pbnh)
 * [Table of contents](#table-of-contents)
 * [Usage](#usage)
    * [Content](#content)
    * [Sunset](#sunset)
    * [Mime](#mime)
 * [Render](#render)

## Usage
You can create pastes with the webui or though the cli using curl. Currently the only way to upload anything other than text or a redirect is through the cli.

Curl has an option for a form id, you can use c or content to specify the contents of a paste.
```
curl -F content=@file.txt servername.com
```
Or you can cat a file
```
cat file.txt | curl -F c=@- servername.com
```
[![asciicast](https://asciinema.org/a/8q5x4a0wrhtm7e2feok4b9i67.png)](https://asciinema.org/a/8q5x4a0wrhtm7e2feok4b9i67)
We also support strings
```
curl -F content="hello world!" servername.com
```
To upload a redirect change the form id to r
```
curl -F r="https://www.google.com" servername.com
```
There are three different inputs allowed in a curl command they are content, sunset, and mime. Sunset and Mime are optional.
### content or c
The content is exactly what it sounds like. The content of the file or the string data you want to paste and can be seen in the examples above.
### sunset
The sunset is the amount of time you want this paste to be available. If sunset is specified you may specify for it to last a maximum of 24 hours. If unspecified the sunset value is 0 and the paste will not be removed.

Currently there is no support for deleting pastes after you create them with a sunset. The sunset is set but no process is cleaning them up.
```
curl -F content=@file.txt -F sunset=10 servername.com
```
### mime
The mime type is the type of file. If you want automatic syntax highlighting through the webui or want an image to be displayed you can set the mimetype.
The default is plain text, pbnh uses [python-magic](https://github.com/ahupp/python-magic) to attempt to guess the buffer mimetype if none is specified.
A list of mimetypes can be found [here](http://www.freeformatter.com/mime-types-list.html). Only specify the second half of the mimetype.
For example for the mimetype 'application/pdf' only specify pdf.
```
curl -F content=@file.txt -F mime=plain servername.com
```
## Rendering
You can render files as the browser would want to see them by specifying .<extension> in the url
Currently things we render with javascript are
* Markdown (.md)
* RST (.rst)
* asciinema (.asciinema)
