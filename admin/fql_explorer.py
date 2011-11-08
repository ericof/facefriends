#-*- coding:utf-8 -*-

import facebook
import os.path
import logging
import wsgiref.handlers
from config import FACEBOOK_APP_SECRET, FACEBOOK_APP_ID
from google.appengine.runtime import DeadlineExceededError
from google.appengine.api.labs import taskqueue
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
from google.appengine.api import memcache
from models import FBUser
from base import BaseFBHandler


class FQLExplorer(BaseFBHandler):
    def get(self):
        args = dict(current_user=self.current_user,
                    facebook_app_id=FACEBOOK_APP_ID)
        self.show(templateName='fql.html',args=args)
        
    
    def post(self):
        query = self.request.get("query",'')
        results = self.runQuery(query)
        args = dict(current_user=self.current_user,
                    facebook_app_id=FACEBOOK_APP_ID,
                    results=results)
        self.show(templateName='fql.html',args=args)
        
    def runQuery(self,query=''):
        user = self.current_user
        fb = facebook.FQL(user.access_token)
        if query:
            query = [q.strip() for q in query.split('\n') if q.strip()]
            if len(query)>1:
                tmpQuery = []
                for line in query:
                    line = line.split('|')
                    tmpQuery.append(line)
                query = dict(tmpQuery)
            else:
                query = query[0]
        if not query:
            query ={"friends":
                        """SELECT uid
                           FROM 
                                user 
                           WHERE 
                                uid in (SELECT uid2 FROM friend WHERE uid1=%s)""" % str(user.id),
                    "friendFriends":
                        """SELECT 
                                uid1,
                                uid2 
                           FROM 
                                friend 
                           WHERE 
                                uid1 IN 
                                (SELECT uid FROM #friends) 
                                AND uid2 in (SELECT uid FROM #friends)
                        """}
        if isinstance(query,(str,unicode)):
            results = fb.query(query = query)
        else:
            results = fb.multiquery(queries = query)
        
        return str(results)
    

def main():
    util.run_wsgi_app(webapp.WSGIApplication([(r"/admin/fql/?.*", FQLExplorer),
                                             ]))


if __name__ == "__main__":
    main()