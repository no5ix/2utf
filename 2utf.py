#!/usr/bin/python
# -*- coding: utf-8 -*-

import os, argparse, textwrap, time
import codecs
import chardet


DEFAULT_CONF = {
    'check_ext_tuple' : ['cpp', 'h', 'uproject', 'cs', 'txt'],
    # 'size_limit': 100 * 1024 ** 2,  # if the file is larger than this size limit, we could skip it. default 100MB
    'codec_chain': ['ascii', 'utf_8_sig', 'chardet'],
    # We will try elements in this list sequentially.
    # If the element is `chardet` we will obtain the result from chardet.
    # If the element is a valid codec name, we will attempt to open the file with the `strict` mode
    # Note: If it contains `ascii`, it must be place as the first one.
    # Note: `utf_8_sig` should have a priority higher than `latin_1`
    'confi_thres': 0.8,
    # We have to set a minimum threshold. Only those target_encoding results returned by chartdet that are above
    # that threshold level would be accepted.
    # See https://github.com/x1angli/cvt2utf/issues/4 for further details
    'base_dir': './',
    'bak_dir_name_prefix': './2utf_bak_' + str(time.strftime("%Y_%m_%d__%H_%M_%S")) + '/',
}


def cli():
    parser = argparse.ArgumentParser(
        description="A tool that converts non-UTF-encoded text files UTF-8 encoded files.",
        epilog=textwrap.dedent('''
            You can use this tool to remove BOM all code files from your source code repo, 
            make c++ files UTF8-compatible so that the project can be compiled on any system locale.            
            '''),
    )

    parser.add_argument(
        '-n',
        'nobak',
        dest='no_bak',
        action='store_true',
        default=False,
        help=textwrap.dedent('''
            Don't create bak files.
        '''),
    )

    tgt_group = parser.add_mutually_exclusive_group()  # This group will be used to specify the target encoding

    tgt_group.add_argument(
        '-t',
        '--target',
        dest='tgt_codec',
        default='utf_8',
        help=textwrap.dedent('''
            If this command line argument is missing, we convert files to UTF-8 without BOM 
            '''),
    )
    tgt_group.add_argument(
        '-b',
        '--addbom',
        dest='tgt_codec',
        action='store_const',
        const='utf_8_sig',
        help=textwrap.dedent('''
            If this command line argument is missing, we convert files to UTF-8 without BOM 
            (i.e. the target encoding would be just `utf_8`, rather than `utf_8_sig`). 
            But, with this flag, we would add BOM in encoded text files (i.e. the target encoding would be 'utf-8-sig').
            '''),
    )

    args = parser.parse_args()

    base = DEFAULT_CONF['base_dir']
    if os.path.isdir(base):
        walk_dir(base, args)
    else:
        convert_file(base, args)

def walk_dir(base, args):
    for root, dirs, files in os.walk(base):
        for name in files:

            extension = os.path.splitext(name)[1][1:].strip().lower()
            if extension in DEFAULT_CONF['check_ext_tuple']:
                fullname = os.path.join(root, name)
                try:
                    convert_file(fullname, args)
                except IOError:
                    pass
                except KeyboardInterrupt:
                    exit()

def convert_file(filename, args):

    # size = os.path.getsize(filename)
    #
    # if size == 0 or size > DEFAULT_CONF['size_limit']:
    #     return

    with open(filename, 'rb') as f:  # read under the binary mode
        file_bytes = f.read()

    src_codec = detect_codec(file_bytes, filename)
    if src_codec is None:
        return

    if src_codec == 'ascii':
        src_codec = 'utf_8'

    if src_codec == args.tgt_codec:
        return

    try:
        file_str = file_bytes.decode(src_codec)
    except UnicodeDecodeError as e:
        return

    if not args.no_bak:
        file_name_tuple = os.path.split(filename)
        new_dir_name = DEFAULT_CONF['bak_dir_name_prefix'] + file_name_tuple[0].replace('./', '')
        new_dir_file_name = new_dir_name + '/' + file_name_tuple[1].replace('/./', '/')
        if not os.path.exists(new_dir_name):
            os.makedirs(new_dir_name, 0755 )
        with open(new_dir_file_name, 'wb') as f:  # write under the binary mode
            f.write(file_bytes)


    with open(filename, 'wb') as f:  # write under the binary mode
        f.write(file_str.encode(args.tgt_codec))

def normalize_codec_name(chardet_name):
    """
    Normalizes chardet codec names to Python codec names.
    :param chardet_name: chardet codec names
    :return: Python codec names. See: https://docs.python.org/3.7/library/codecs.html#standard-encodings
    """

    python_name = chardet_name.lower().replace('iso-', 'iso').replace('-', '_')
    python_name = codecs.lookup(python_name).name

    # Since chardet only recognized all GB-based target_encoding as 'gb2312', the decoding will fail when the text file
    # contains certain special charaters. To make it more special-character-tolerant, we should
    # upgrade the target_encoding to 'gb18030', which is a character set larger than gb2312.
    if python_name == 'gb2312':
        return 'gb18030'

    return python_name

def detect_codec(bytedata, filename):

    for codec in DEFAULT_CONF['codec_chain']:
        if codec == 'chardet':
            chr_res = chardet.detect(bytedata)
            if not chr_res['encoding'] or chr_res['confidence'] < DEFAULT_CONF['confi_thres']:
                return None
            else:
                return normalize_codec_name(chr_res['encoding'])
        else:
            try:
                bytedata.decode(codec, 'strict')
                return codec
            except UnicodeDecodeError:
                continue

    return None


if __name__ == '__main__':
    cli()
