#!/usr/bin/env python3

import datetime
import os
import subprocess
import praw
import mutagen
from pathlib import Path
from DB import DB


def get_valid_posts():
    r = praw.Reddit(user_agent='listentothis v1 by /u/znuxor')
    sub = r.subreddit('listentothis')
    content = sub.top('week')
    posts = list()
    for post in content:
        if post.score >= 100 and post.media is not None and ('youtu.be' in post.url or post.media['type'] == 'youtube.com'):
            post_uid = post.id
            post_date = datetime.datetime.fromtimestamp(post.created)
            the_link = post.url
            if 'youtu.be' in the_link:
                the_link = the_link[0:28]
            elif 'attribution' in the_link:
                continue
            elif 'playlist' in the_link:
                continue
            else:
                the_link = the_link[0:43]
            the_title = post.title
            posts.append((post_uid, post_date, the_link, the_title))
    return posts


# Get the ID of the first phone
phone_id = str(subprocess.check_output(['kdeconnect-cli', '-a', '--id-only']))[2:][:-3]

subprocess.run(['kdeconnect-cli', '-d', phone_id, '--ping-msg', 'listentothis.py started!'])

# Initialize the DB
db_obj = DB(Path(os.path.expanduser('~')) / '.listentothis' / 'database.pickle')

# Get and parse the reddit posts
the_posts = get_valid_posts()
for (an_uid, a_date, a_link, a_title) in the_posts:
    if not db_obj.id_exists(an_uid):
        db_obj.add_item(an_uid, a_title, a_date, a_link)
        print(a_title + ' added to the database.')
        subprocess.run(['kdeconnect-cli', '-d', phone_id, '--ping-msg', a_title + ' added to the database.'])


# Download the non-downloaded objects
for an_uid in db_obj.get_uids():
    if not db_obj.is_downloaded(an_uid):
        print(db_obj.get_name(an_uid))
        if 'playlist' in db_obj.get_name(an_uid).lower():
            continue
        try:
            db_obj.try_download(an_uid)
        except mutagen.MutagenError:
            continue
        print(db_obj.get_name(an_uid)+' downloaded.')
        subprocess.run(['kdeconnect-cli', '-d', phone_id, '--ping-msg', db_obj.get_name(an_uid)+' downloaded.'])


# Hack to get the phone to access the phone's filesystem
try:
    subprocess.run(['dolphin', 'kdeconnect://'+phone_id+'/'], timeout=5)
except subprocess.TimeoutExpired:
    pass
subprocess.run(['kdeconnect-cli', '-d', phone_id, '--ping-msg', 'phone probably mounted'])


phone_dir_path = '/run/user/1000/' + phone_id + '/primary/Music/weekly/'


# Sync the files to the phone if not already done so
for an_uid in db_obj.get_uids():
    if not db_obj.is_synced(an_uid):
        print(db_obj.get_name(an_uid))
        try:
            db_obj.sync(an_uid, phone_dir_path)
        except FileNotFoundError:
            pass
        finally:
            print(an_uid + ' synced.')
            subprocess.run(['kdeconnect-cli', '-d', phone_id, '--ping-msg', db_obj.get_name(an_uid)+' synced!'])


# Delete the old songs
for an_uid in db_obj.get_uids():
    try:
        if db_obj.is_rotten(an_uid):
            the_name = db_obj.get_name(an_uid)
            try:
                db_obj.try_remote_delete(an_uid, phone_dir_path)
            except FileNotFoundError:
                continue
            subprocess.run(['kdeconnect-cli', '-d', phone_id, '--ping-msg', the_name+' removed!'])
    except TypeError:
        continue

subprocess.run(['kdeconnect-cli', '-d', phone_id, '--ping-msg', 'listentothis completed!'])
