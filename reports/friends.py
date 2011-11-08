#!/Users/erico/Documents/Pessoal/OutrosProjetos/Facebook/py2.6/bin/python
#
# Copyright 2010 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""A barebones AppEngine application that uses Facebook for login."""

import facebook
import os.path
import logging
from config import FACEBOOK_APP_ID, FACEBOOK_APP_SECRET
import wsgiref.handlers
from google.appengine.runtime import DeadlineExceededError
from google.appengine.api.labs import taskqueue
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
from django.utils import simplejson as json
from google.appengine.api import memcache
from cgi import escape

from models import FBUser

class FriendsReport(webapp.RequestHandler):
    last = 0
    def get(self):
        uid = self.request.get("uid",'534881870')
        # Key
        #userKey = escape(self.request.get('uk','')
        #user = db.get(userKey)
        user = FBUser.get_by_key_name(uid)
        friends = memcache.get(key='FriendReports_%s' % uid)
        if not friends and user:
            friends = FBUser.gql('WHERE friends = :1 ORDER BY name,id',user.key()).run()
            memcache.add(key='FriendReports_%s' % str(user.id),value=friends,time=240)
        if user:
            data = [{'name':f.name,
                     'id':f.id,
                     'pic':'http://graph.facebook.com/%s/picture?type=square' % f.id,
                     'friends':[ff.id_or_name() for ff in f.friends]} for f in friends]
            self.response.out.write(json.dumps(data))

def main():
    util.run_wsgi_app(webapp.WSGIApplication([(r"/myFriends.json", FriendsReport),
                                             ]))


if __name__ == "__main__":
    main()
