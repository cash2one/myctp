#! /usr/bin/env python
# coding=utf-8
import requests
import json


def get_token():
    url = 'https://qyapi.weixin.qq.com/cgi-bin/gettoken'
    values = {'corpid': 'wxcaa6d6f086ba8ac2',
              'corpsecret': 'msm8a3TF4YwGcyWJTbtdVDue-6dYtx7QbbH35f1K0Ii9Oev_HKlZleL3ouV6HDaI',
              }
    req = requests.post(url, params=values)
    data = json.loads(req.text)
    return data["access_token"]


def send_msg(msg):
    url = "https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=" + get_token()
    values = """{"touser" : "lhq2818" ,
                "toparty":"ElevenTeam",
                "msgtype":"text",
                "agentid":"1",
                "text":{
                "content": "%s"
                        },
                "safe":"0"
                }""" % (str(msg))

    data = json.loads(values)
    req = requests.post(url, values)
