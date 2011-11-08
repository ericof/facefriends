#-*- coding:utf-8 -*-

"""Aplicacao de exemplo do appengine com facebook"""

import facebook
import os.path
import wsgiref.handlers
import logging
from config import FACEBOOK_APP_ID,FACEBOOK_APP_SECRET

from google.appengine.runtime import DeadlineExceededError
from google.appengine.api.labs import taskqueue
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
from google.appengine.api import memcache

from models import FBUser

class QueueHandler(webapp.RequestHandler):
    ''' Handler for home page
    '''
    def get(self):
        ''' Let's get the friends of this user
        '''
        users = FBUser.gql("WHERE accessed = TRUE").run()
        for user in users:
            logging.debug(user.id)
            taskqueue.add(url='/queue/getFriends', params={'user_id':user.id})
        self.response.out.write('Feito')


def main():
    util.run_wsgi_app(webapp.WSGIApplication([
                                              (r"/admin/process/?.*", QueueHandler),
                                             ]))

if __name__ == "__main__":
    main()
