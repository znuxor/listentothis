import datetime
import os
import shutil
import pickle
import slugify
import youtube_dl
from typing import List
from dataclasses import dataclass
from mutagen.easyid3 import EasyID3

@dataclass
class Item:
    uid: str
    download_date: datetime.datetime
    name: str
    filename: str
    link: str
    synced_to_phone: bool = False

class DB:
    def __init__(self, init_file_path):
        if not os.path.isfile(init_file_path):
            self.items: List[Item] = list()
            self.init_file_path = init_file_path
            dir_path = os.path.split(self.init_file_path)[0]
            try:
                os.mkdir(dir_path)
            except:
                pass
            self.last_subreddit_check = datetime.datetime.now() - datetime.timedelta(days=9)
            with open(self.init_file_path, 'wb') as new_file:
                pickle.dump(self, new_file)
        else:
            temp = pickle.load(open(init_file_path, 'rb'))
            self.last_subreddit_check = temp.last_subreddit_check
            self.init_file_path = init_file_path
            self.items = temp.items

    def id_exists(self, uid):
        exists = False
        for item in self.items:
            if item.uid == uid:
                exists = True
                break
        return exists

    def add_item(self, uid, name, date, link):
        self.items.append(Item(uid, None, name, slugify.slugify(name)+'.mp3', link))
        with open(self.init_file_path, 'wb') as new_file:
            pickle.dump(self, new_file)

    def get_uids(self):
        return tuple(i.uid for i in self.items)

    def find_index(self, uid):
        for i in range(len(self.items)):
            if self.items[i].uid == uid:
                return i
        raise KeyError("The uid is not in the DB!")

    def is_downloaded(self, uid):
        if not self.id_exists(uid):
            raise KeyError("The uid is not in the DB!")
        index = self.find_index(uid)
        return self.items[index].download_date != None

    def is_synced(self, uid):
        if not self.id_exists(uid):
            raise KeyError("The uid is not in the DB!")
        index = self.find_index(uid)
        return self.items[index].synced_to_phone != False

    def sync(self, uid, dest_path):
        if not self.id_exists(uid):
            raise KeyError("The uid is not in the DB!")
        index = self.find_index(uid)
        file_path = os.path.split(self.init_file_path)[0]
        file_path = os.path.join(file_path, self.items[index].filename)
        shutil.copy(file_path, dest_path)
        self.items[index].synced_to_phone = True
        with open(self.init_file_path, 'wb') as new_file:
            pickle.dump(self, new_file)

    def is_rotten(self, uid):
        if not self.id_exists(uid):
            raise KeyError("The uid is not in the DB!")
        index = self.find_index(uid)
        return self.items[index].download_date <= datetime.datetime.now()-datetime.timedelta(days=8)

    def delete_from_db(self, uid, skip_delete=False):
        if not self.id_exists(uid):
            raise KeyError("The uid is not in the DB!")
        index = self.find_index(uid)
        file_path = os.path.join(os.path.split(self.init_file_path)[0], self.items[index].filename)
        if not skip_delete:
            os.remove(file_path)
        self.items.pop(index)
        with open(self.init_file_path, 'wb') as new_file:
            pickle.dump(self, new_file)

    def try_remote_delete(self, uid, dest_path):
        if not self.id_exists(uid):
            raise KeyError("The uid is not in the DB!")
        index = self.find_index(uid)
        file_path = os.path.join(dest_path, self.items[index].filename)
        os.remove(file_path)
        with open(self.init_file_path, 'wb') as new_file:
            pickle.dump(self, new_file)
        self.delete_from_db(uid)

    def try_download(self, uid):
        if not self.id_exists(uid):
            raise KeyError("The uid is not in the DB!")
        index = self.find_index(uid)

        filename = self.items[index].filename
        dirpath_to_file = os.path.split(self.init_file_path)[0]
        path_to_file = os.path.join(dirpath_to_file, filename)
        downloadOPTS = {
            'quiet': True,
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192'
            }],
            'outtmpl': os.path.join(dirpath_to_file, filename[:-4]+'.%(ext)s')
        }

        with youtube_dl.YoutubeDL(downloadOPTS) as ydl:
            try:
                print(self.items[index].link)
                print(self.items[index].name)
                ydl.download([self.items[index].link])
            except:
                print(self.items[index].link)
                print(self.items[index].name)
            else:
                metatag = EasyID3(path_to_file)
                metatag['title'] = self.items[index].name
                metatag['artist'] = "listentothis"
                metatag.save()

                self.items[index].download_date = datetime.datetime.now()
                with open(self.init_file_path, 'wb') as new_file:
                    pickle.dump(self, new_file)

    def get_name(self, uid):
        for item in self.items:
            if item.uid == uid:
                return item.name

    def get_date(self, uid):
        for item in self.items:
            if item.uid == uid:
                return item.download_date
