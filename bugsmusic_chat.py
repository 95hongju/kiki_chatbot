import re
import json
import random
import time
import urllib.request
from bs4 import BeautifulSoup
from flask import Flask, request
from slack import WebClient
from slack.web.classes import extract_json
from slack.web.classes.blocks import *
from slack.web.classes.elements import *
from slack.web.classes.interactions import MessageInteractiveEvent
from slackeventsapi import SlackEventAdapter


SLACK_TOKEN = ""
SLACK_SIGNING_SECRET = ""


app = Flask(__name__)
# /listening 으로 슬랙 이벤트를 받습니다.
slack_events_adaptor = SlackEventAdapter(SLACK_SIGNING_SECRET, "/listening", app)
slack_web_client = WebClient(token=SLACK_TOKEN)

def show_menu_list():
    button_actions = ActionsBlock(
        elements=[
            ButtonElement(
                text="실시간차트",style="primary",
                action_id="chart_current",value = "chart_current"
            ),
            ButtonElement(
                text="장르별차트", style="danger",
                action_id="chart_genre",value = "chart_genre"
            ),
            ButtonElement(
                text="오늘의 노래추천",
                action_id="chart_album",value = "chart_album"
            ),

        ]
    )
    return [button_actions]

def today_musics():

    url = "https://music.bugs.co.kr/connect/chart/track/day/connectall"
    source_code = urllib.request.urlopen(url).read()
    soup = BeautifulSoup(source_code, "html.parser")

    recos = soup.find('table', class_='list trackList').find('tbody')
    p_titles = recos.find_all('p', class_='title')
    p_artists = recos.find_all('p', class_='artist')
    p_imgs = recos.find_all('a', class_='thumbnail')

    titles = [title.find('a').get_text() for title in p_titles]
    artists = [artist.find('a').get_text() for artist in p_artists]
    imgs = [img.find('img')['src'] for img in p_imgs]

    random_list = {}

    for idx,(title, artist, img) in enumerate(zip(titles, artists, imgs)):

        random_list[idx] = [title, artist, img]

    random_recommand= [random.randint(0,len(random_list)) for r in range(3)]
    print(random_recommand)

    message_list = []
    attachments_list = []

    for s in range(len(random_recommand)):
        tmp = random_list[random_recommand[s]]
        print(tmp)
        tmp_txt = '{} / {}'.format(tmp[0], tmp[1])


        attachments = [{"text": tmp_txt,
                        "thumb_url": tmp[2]}]
        message_list.append('')
        attachments_list.append(attachments)


    return message_list, attachments_list


def genre_crawl(sel):

    genre = ["ballad","rnh","rns","elec","rock"]

    url = "https://music.bugs.co.kr/genre/chart/kpop/" + genre[sel-1] + "/total/day"
    source_code = urllib.request.urlopen(url).read()
    soup = BeautifulSoup(source_code, "html.parser")

    #upper message
    message = {}
    views = soup.find("table", class_="list trackList byChart").find('tbody')
    titles_p = views.find_all('p', class_='title')
    artists_p = views.find_all('p', class_= 'artist')
    imgs_p = views.find_all('a', class_="thumbnail")

    titles = [tit.find("a").get_text() for tit in titles_p]
    artists = [tit.find("a").get_text() for tit in artists_p]
    imgs = [tit.find("img")['src'] for tit in imgs_p]

    i = 0
    for title, artist in zip(titles, artists):
        message[i] = [title, artist]
        i += 1

    rtn_msg = []
    rtn_att = []

    for num in range(0,10):
        txt = "{}위 : {} / {}".format(num + 1, message[num][0], message[num][1])
        attachments = [{"text": txt, "thumb_url": imgs[num]}]

        rtn_msg.append('')
        rtn_att.append(attachments)

    return rtn_msg, rtn_att




def _crawl_music_chart():

    url = "https://music.bugs.co.kr/chart"
    source_code = urllib.request.urlopen(url).read()
    soup = BeautifulSoup(source_code, "html.parser")


    message_list = []
    attachments_list = []

    total_table = soup.find('table',class_='list trackList byChart').find('tbody').find_all('tr')

    for idx,row in enumerate(total_table[:10]):
        thumbs = row.find('img')['src']
        title = row.find('p',class_='title').find('a')['title']
        artist = row.find('p',class_='artist').find('a')['title']

        txt = '{}위: {} / {}'.format(idx+1,title,artist)

        attachments = [{"text": txt,
                        "thumb_url": thumbs}]
        message_list.append('')
        attachments_list.append(attachments)


    return message_list, attachments_list


# 챗봇이 멘션을 받았을 경우
@slack_events_adaptor.on("app_mention")
def app_mentioned(event_data):
    channel = event_data["event"]["channel"]
    text = event_data["event"]["text"]

    if 'music' in text:
        message = show_menu_list()
        slack_web_client.chat_postMessage(
        channel=channel,
        blocks=extract_json(message)
        )


    elif text[-1].isdigit():

        tmp = [1,2,3,4,5]
        if int(text[-1]) in tmp:
            # 있는경우
            sel = int(text[-1])
            message_list,attachments_list = genre_crawl(sel)

            for i in range(len(message_list)):
                slack_web_client.chat_postMessage(
                    channel=channel,
                    text = message_list[i],
                    attachments = attachments_list[i]
                )
                time.sleep(1)

        else:
            #없는경우 메세지 출력
            slack_web_client.chat_postMessage(
            channel=channel,
            text = "`@<봇이름> music` 과 같이 멘션해주세요."
            )

    else:
        slack_web_client.chat_postMessage(
        channel=channel,
        text = "`@<봇이름> music` 과 같이 멘션해주세요."
        )

    return "OK", 200



#button click
@app.route("/click", methods=["GET", "POST"])
def on_button_click():
    # 버튼 클릭은 SlackEventsApi에서 처리해주지 않으므로 직접 처리합니다
    payload = request.values["payload"]
    click_event = MessageInteractiveEvent(json.loads(payload))
    ordertxt = str(click_event.value)


    if 'chart_current' in ordertxt:
        message_list,attachments_list = _crawl_music_chart()

        for i in range(len(message_list)):
            slack_web_client.chat_postMessage(
                channel=click_event.channel.id,
                text = message_list[i],
                attachments = attachments_list[i]
            )
            time.sleep(1)
#-------------작업중
    #when yser clicked 장르별차트
    elif 'chart_genre' in ordertxt:

        slack_web_client.chat_postMessage(
            channel=click_event.channel.id,
            text = "`@<봇이름> [(발라드/댄스/팝)은 1,(랩/힙합)은 2,(알앤비/소울)은 3,(일렉트로닉)은 4,(락/메탈)은 5]` 과 같이 멘션해주세요."
            )

    #when user clicked 오늘의 노래
    elif 'chart_album' in ordertxt:
        message_list,attachments_list = today_musics()
        for i in range(len(message_list)):
            slack_web_client.chat_postMessage(
                channel=click_event.channel.id,
                text = message_list[i],
                attachments = attachments_list[i]
            )
            time.sleep(1)

    return "OK", 200

# / 로 접속하면 서버가 준비되었다고 알려줍니다.
@app.route("/", methods=["GET"])
def index():
    return "<h1>Server is ready.</h1>"


if __name__ == '__main__':
    app.run('0.0.0.0', port=8080)
