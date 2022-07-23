#!/usr/bin/env python3
# encoding: utf-8
import json
import time
import requests
import datetime

from cortexutils.analyzer import Analyzer

def logprint(message,data):
    date= datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
    filelog = open("/var/log/cortex_analyzers/cortex_coa.log","a")
    filelog.write("[" + str(date) + "]" + "[" + message + "]" + str(data) + "\n")
    filelog.close()


class SOCCRATES_coagen_analyzer(Analyzer):

    def __init__(self):
        Analyzer.__init__(self)
        self.service = self.get_param('config.service', None, 'Service parameter is missing')
        self.coaGen_url = self.get_param('config.url', None, 'Missing URL of the COA Generator tool')
        self.scad_url = self.get_param('config.scad_url', None)
        self.username = self.get_param('config.username', None)
        self.password = self.get_param('config.password', None)
        self.organization_name = self.get_param('config.organization_name', None)
        self.project_name = self.get_param('config.project_name', None)
        self.scenario_name = self.get_param('config.scenario_name', None)




    def check_response(self, response):
        status=response.status_code
        if status == 400:
            logprint("Response Error",str(status) + " - " + str(response.content))
            self.error('Status: ' + str(status) + " - " + str(response.content))
        return response


    def run(self):
        if self.service == 'coagen':
            #get input
            if self.data_type == 'other':
                inputData = self.get_param('data')
                logprint("input", inputData)
                jsonData = json.loads(inputData)
                jsonData["scad_url"] = self.scad_url
                jsonData["username"] = self.username
                jsonData["password"] = self.password
                jsonData["organization_name"] = self.organization_name
                jsonData["project_name"] = self.project_name
                jsonData["scenario_name"] = self.scenario_name
                input = json.dumps(jsonData)
                logprint("changedInput", input)
                response = requests.post(self.coaGen_url,input)
                self.check_response(response)
                logprint("output", response.content)
                #logprint("RESPONSE HERE:")
                #logprint(response.content)
                self.report(json.loads(response.content))
            else:
                self.error('Invalid data type')

        else:
            self.error('Invalid service')


if __name__ == '__main__':
    SOCCRATES_coagen_analyzer().run()
