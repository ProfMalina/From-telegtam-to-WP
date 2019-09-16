# -*- coding: utf-8 -*-

from os import remove
from PIL import Image
from telethon import TelegramClient, events
from telethon.tl.types import PeerChannel
from wordpress_xmlrpc import Client, WordPressPost, WordPressUser
from wordpress_xmlrpc.compat import xmlrpc_client
from wordpress_xmlrpc.methods import posts, media, users
import re


api_id = API_ID_FROM_TELEGA
api_hash = 'API_HASH_FROM_TELEGA'
CHAT_NAME = 'CHAT_NAME'
client = TelegramClient('NAME_SESSION', api_id, api_hash)

wp = Client('https://PATH/TO/xmlrpc.php', 'LOGIN', 'PASS')


def add_http(url):
    ptrn = r'^(https?:)'
    res = re.findall(ptrn, url)
    if res:
        return url
    else:
        return 'http://' + url


def tit_le(msg, debug=False):
    if debug:
        title = 1
        content = 2
    entities = sorted(msg['entities'], key=lambda x: x['offset'], reverse=True)
    message = msg['message']
    try:
        for i in entities:
            start = i['offset']
            finish = i['offset'] + i['length']
            text = message[start:finish]
            if i['_'] == 'MessageEntityUrl':
                url = text
                message = message[:start] + '<a href=' + add_http(url) + '>' + text + '</a>' + message[finish:]
            if i['_'] == 'MessageEntityBold':
                message = message[:start] + '<b>' + text + '</b>' + message[finish:]
            if i['_'] == 'MessageEntityTextUrl':
                url = i['url']
                message = message[:start] + '<a href=' + add_http(url) + '>' + text + '</a>' + message[finish:]
            else:
                continue
        ptrn_w_h = r'\#\w*\s?\s?'
        str_without_hash = re.sub(ptrn_w_h, '', message)
        ptrn = r'^.{7,70}\s[^<]'
        str_without_hash = str_without_hash.strip()
        try:
            title = re.search(ptrn, str_without_hash).group(0)
        except:
            title = re.search(ptrn, str_without_hash)
        content = str_without_hash.replace(str(title), '')
        return title, content
    except Exception as err:
        print(err)


def scale_image(input_image_path,
                output_image_path,
                width=None,
                height=None
                ):
    original_image = Image.open(input_image_path)
    w, h = original_image.size
    print('The original image size is {wide} wide x {height} '
          'high'.format(wide=w, height=h))

    if width and height:
        max_size = (width, height)
    elif width:
        max_size = (width, h)
    elif height:
        max_size = (w, height)
    else:
        # No width or height specified
        raise RuntimeError('Width or height required!')

    original_image.thumbnail(max_size, Image.ANTIALIAS)
    original_image.save(output_image_path)

    scaled_image = Image.open(output_image_path)
    width, height = scaled_image.size
    print('The scaled image size is {wide} wide x {height} '
          'high'.format(wide=width, height=height))


@client.on(events.NewMessage(chats='CHAT_NAME'))
async def normal_handler(event):
    post = WordPressPost()
    msg = event.message.to_dict()
    fwd_channel_name = (await client.get_entity(PeerChannel(msg['fwd_from']['channel_id']))).username
    title, content = tit_le(msg)
    post.title = '@' + fwd_channel_name + ': ' + title
    post.content = content
    post.id = wp.call(posts.NewPost(post))
    post.post_status = 'publish'
    # add image
    # set to the path to your file
    try:
        filename = (await event.message.download_media())
        data = {
            'name': 'picture.jpg',
            'type': 'image/jpeg',  # mimetype
        }
        with open(filename, 'rb') as img:
            data['bits'] = xmlrpc_client.Binary(img.read())
        response = wp.call(media.UploadFile(data))
        attachment_id = response['id']
        post.thumbnail = attachment_id
        # delete pictures
        remove(filename)
    except:
        print("with out pictures")

    wp.call(posts.EditPost(post.id, post))


client.start()
client.run_until_disconnected()
