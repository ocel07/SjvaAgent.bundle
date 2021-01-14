# -*- coding: utf-8 -*-
import os, traceback, json, urllib, re, unicodedata, urllib2
from .agent_base import AgentBase


class ModuleOttShow(AgentBase):
    module_name = 'ott_show'

    def search(self, results, media, lang, manual):
        try:
            keyword = self.get_search_keyword(media, manual, from_file=True)
            keyword = keyword.replace(' ', '-')

            Log('SEARCH : %s' % keyword)

            search_data = self.send_search(self.module_name, keyword, manual)

            if search_data is None:
                return
            Log(json.dumps(search_data, indent=4))

            
            def func(show_list):
                for idx, item in enumerate(show_list):
                    meta = MetadataSearchResult(id=item['code'], name=item['title'], score=item['score'], thumb=item['image_url'], lang=lang)
                    meta.summary = item['site'] + ' ' + item['studio']
                    meta.type = "movie"
                    results.Append(meta)
            if 'tving' in search_data:
                func(search_data['tving'])
            if 'wavve' in search_data:
                func(search_data['wavve'])

        except Exception as e: 
            Log('Exception:%s', e)
            Log(traceback.format_exc())

    def update_info(self, metadata, meta_info):
        metadata.original_title = metadata.title
        metadata.title_sort = unicodedata.normalize('NFKD', metadata.title)
        metadata.studio = meta_info['studio']
        metadata.originally_available_at = Datetime.ParseDate(meta_info['premiered']).date()
        metadata.content_rating = meta_info['mpaa']
        metadata.summary = meta_info['plot']
        metadata.genres.clear()
        for tmp in meta_info['genre']:
            metadata.genres.add(tmp)
        
        # 부가영상
        for item in meta_info['extras']:
            if item['mode'] == 'mp4':
                url = 'sjva://sjva.me/video.mp4/%s' % item['content_url']
            elif item['mode'] == 'kakao':
                url = 'sjva://sjva.me/kakao.mp4/%s' % item['content_url']
            metadata.extras.add(self.extra_map[item['content_type']](url=url, title=self.change_html(item['title']), originally_available_at=Datetime.ParseDate(item['premiered']).date(), thumb=item['thumb']))

        # rating
        for item in meta_info['ratings']:
            if item['name'] == 'tmdb':
                metadata.rating = item['value']
                metadata.audience_rating = 0.0

        # role
        metadata.roles.clear()
        for item in ['actor', 'director', 'credits']:
            for item in meta_info[item]:
                actor = metadata.roles.new()
                actor.role = item['role']
                actor.name = item['name']
                actor.photo = item['thumb']

        # poster
        ProxyClass = Proxy.Preview if meta_info['plex_is_proxy_preview'] else Proxy.media
        valid_names = []
        poster_index = art_index = banner_index = 0
        for item in sorted(meta_info['thumb'], key=lambda k: k['score'], reverse=True):
            valid_names.append(item['value'])
            if item['aspect'] == 'poster':
                if item['thumb'] == '':
                    metadata.posters[item['value']] = ProxyClass(HTTP.Request(item['value']).content, sort_order=poster_index+1)
                else:
                    metadata.posters[item['value']] = ProxyClass(HTTP.Request(item['thumb']).content, sort_order=poster_index+1)
                poster_index += 1
            elif item['aspect'] == 'landscape':
                if item['thumb'] == '':
                    metadata.art[item['value']] = ProxyClass(HTTP.Request(item['value']).content, sort_order=art_index+1)
                else:
                    metadata.art[item['value']] = ProxyClass(HTTP.Request(item['thumb']).content, sort_order=art_index+1)
                art_index += 1
            elif item['aspect'] == 'banner':
                if item['thumb'] == '':
                    metadata.banners[item['value']] = ProxyClass(HTTP.Request(item['value']).content, sort_order=banner_index+1)
                else:
                    metadata.banners[item['value']] = ProxyClass(HTTP.Request(item['thumb']).content, sort_order=banner_index+1)
                banner_index += 1

        metadata.posters.validate_keys(valid_names)
        metadata.art.validate_keys(valid_names)
        metadata.banners.validate_keys(valid_names)





    def update_episode(self, show_epi_info, episode, frequency=None):
        try:
            valid_names = []

            if 'daum' in show_epi_info:
                #if 'tving_id' in meta_info['extra_info']:
                #    param += ('|' + 'V' + meta_info['extra_info']['tving_id'])
                episode_info = self.send_episode_info(self.module_name, show_epi_info['daum']['code'])
                Log(episode_info)

                episode.originally_available_at = Datetime.ParseDate(episode_info['premiered']).date()
                episode.title = episode_info['title']
                episode.summary = episode_info['plot']

                thumb_index = 30
                ott_mode = 'only_thumb'
                for item in sorted(episode_info['thumb'], key=lambda k: k['score'], reverse=True):
                    valid_names.append(item['value'])
                    if item['thumb'] == '':
                        episode.thumbs[item['value']] = Proxy.Preview(HTTP.Request(item['value']).content, sort_order=thumb_index+1)
                    else:
                        episode.thumbs[item['value']] = Proxy.Preview(HTTP.Request(item['thumb']).content, sort_order=thumb_index+1)
                    thumb_index += 1
                    ott_mode = 'stop'
                
                # 부가영상
                for item in episode_info['extras']:
                    if item['mode'] == 'mp4':
                        url = 'sjva://sjva.me/video.mp4/%s' % item['content_url']
                    elif item['mode'] == 'kakao':
                        url = 'sjva://sjva.me/kakao.mp4/%s' % item['content_url']
                    episode.extras.add(self.extra_map[item['content_type']](url=url, title=self.change_html(item['title']), originally_available_at=Datetime.ParseDate(item['premiered']).date(), thumb=item['thumb']))
            else:
                ott_mode = 'full'

            if ott_mode != 'stop':
                for site in ['tving', 'wavve']:
                    if site in show_epi_info:
                        if ott_mode == 'full':
                            episode.originally_available_at = Datetime.ParseDate(show_epi_info[site]['premiered']).date()
                            episode.title = show_epi_info[site]['premiered']
                            if frequency is not None:
                                episode.title = u'%s회 (%s)' % (frequency, episode.title)
                            episode.summary = show_epi_info[site]['plot']

                        if ott_mode in ['full', 'only_thumb']:
                            thumb_index = 20
                            valid_names.append(show_epi_info[site]['thumb'])
                            episode.thumbs[show_epi_info[site]['thumb']] = Proxy.Preview(HTTP.Request(show_epi_info[site]['thumb']).content, sort_order=thumb_index+1)
                
            episode.thumbs.validate_keys(valid_names)

        except Exception as e: 
            Log('Exception:%s', e)
            Log(traceback.format_exc())



    def update(self, metadata, media, lang):
        #self.base_update(metadata, media, lang)
        try:
            flag_ending = False
            flag_media_season = False
            if len(media.seasons) > 1:
                for media_season_index in media.seasons:
                    if int(media_season_index) > 1 and int(media_season_index) < 1900:
                        flag_media_season = True
                        break

            search_data = self.send_search(self.module_name, media.title, False)        
            # data = get_show_list(media.title)
            # sort

            index_list = [index for index in media.seasons]
            index_list = sorted(index_list)
            #for media_season_index in media.seasons:
            for media_season_index in index_list:
                Log('media_season_index is %s', media_season_index)
                if media_season_index == '0':
                    continue
                search_title = media.title.replace(u'[종영]', '')
                search_title = search_title.split('|')[0]
                search_code = metadata.id            
                if flag_media_season and len(search_data['series']) > 1:
                    search_title = search_data['series'][int(media_season_index)-1]['title']
                    search_code = search_data['series'][int(media_season_index)-1]['code']

                Log('flag_media_season : %s', flag_media_season)
                Log('search_title : %s', search_title)
                Log('search_code : %s', search_code)

                meta_info = self.send_info(self.module_name, search_code, title=search_title)
                Log('aaaaaaaaaaaaaaaaaaaaaaaaaaa')
                Log(meta_info)

                if flag_media_season:
                    metadata.title = media.title.split('|')[0].strip()
                else:
                    metadata.title = meta_info['title']
                metadata.original_title = metadata.title                  
                metadata.title_sort = unicodedata.normalize('NFKD', metadata.title)
                
                self.update_info(metadata, meta_info)
                metadata_season = metadata.seasons[media_season_index]

                # 포스터
                # Get episode data.
                @parallelize
                def UpdateEpisodes():
                    Log('111111111111111111111111111')
                    for media_episode_index in media.seasons[media_season_index].episodes:
                        episode = metadata.seasons[media_season_index].episodes[media_episode_index]

                        @task
                        def UpdateEpisode(episode=episode, media_season_index=media_season_index, media_episode_index=media_episode_index):
                            Log('EEEEEEEEEEEEEPISODE')
                            Log(media_episode_index)

                            frequency = False
                            show_epi_info = None
                            if media_episode_index in meta_info['extra_info']['episodes']:
                                show_epi_info = meta_info['extra_info']['episodes'][media_episode_index]
                                self.update_episode(show_epi_info, episode)
                            else:
                                #에피정보가 없다면 
                                match = Regex(r'\d{4}-\d{2}-\d{2}').search(media_episode_index)
                                if match:
                                    for key, value in meta_info['extra_info']['episodes'].items():
                                        if ('daum' in value and value['daum']['premiered'] == media_episode_index) or ('tving' in value and value['tving']['premiered'] == media_episode_index) or ('wavve' in value and value['wavve']['premiered'] == media_episode_index):
                                            show_epi_info = value
                                            self.update_episode(show_epi_info, episode, frequency=key)
                                            break
                            if show_epi_info is None:
                                return

                            episode.directors.clear()
                            episode.producers.clear()
                            episode.writers.clear()
                            for item in meta_info['credits']:
                                meta = episode.writers.new()
                                meta.role = item['role']
                                meta.name = item['name']
                                meta.photo = item['thumb']
                            for item in meta_info['director']:
                                meta = episode.directors.new()
                                meta.role = item['role']
                                meta.name = item['name']
                                meta.photo = item['thumb']
                            
                            


            # 시즌 title, summary
            if not flag_media_season:
                return
            url = 'http://127.0.0.1:32400/library/metadata/%s' % media.id
            data = JSON.ObjectFromURL(url)
            section_id = data['MediaContainer']['librarySectionID']
            token = Request.Headers['X-Plex-Token']
            for media_season_index in media.seasons:
                Log('media_season_index is %s', media_season_index)
                if media_season_index == '0':
                    continue
                filepath = media.seasons[media_season_index].all_parts()[0].file
                tmp = os.path.basename(os.path.dirname(filepath))
                season_title = None
                if tmp != metadata.title:
                    Log(tmp)
                    match = Regex(r'(?P<season_num>\d{1,4})\s*(?P<season_title>.*?)$').search(tmp)
                    if match:
                        Log('season_num : %s', match.group('season_num'))
                        Log('season_title : %s', match.group('season_title'))
                        if match.group('season_num') == media_season_index and match.group('season_title') is not None:
                            season_title = match.group('season_title')
                metadata_season = metadata.seasons[media_season_index]
                if season_title is None:
                    url = 'http://127.0.0.1:32400/library/sections/%s/all?type=3&id=%s&summary.value=%s&X-Plex-Token=%s' % (section_id, media.seasons[media_season_index].id, urllib.quote(metadata_season.summary.encode('utf8')), token)
                else:
                    url = 'http://127.0.0.1:32400/library/sections/%s/all?type=3&id=%s&title.value=%s&summary.value=%s&X-Plex-Token=%s' % (section_id, media.seasons[media_season_index].id, urllib.quote(season_title.encode('utf8')), urllib.quote(metadata_season.summary.encode('utf8')), token)
                request = PutRequest(url)
                response = urllib2.urlopen(request)



        except Exception as e: 
            Log('Exception:%s', e)
            Log(traceback.format_exc())




def get_show_list(name, id=None):
    try:
        Log('get_show_list : %s %s', name, id)
        url = 'https://search.daum.net/search?q=%s' % (urllib.quote(name.encode('utf8')))
        Log(url)
        root = HTML.ElementFromURL(url)
        return DaumTV.get_show_info_on_home(root)
    except Exception as e:
        Log('Exception:%s', e)
        Log(traceback.format_exc())

class PutRequest(urllib2.Request):
    def __init__(self, *args, **kwargs):
        return urllib2.Request.__init__(self, *args, **kwargs)

    def get_method(self, *args, **kwargs):
        return 'PUT'
