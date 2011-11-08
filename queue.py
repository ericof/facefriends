#-*- coding:utf-8 -*-
# 
"""A barebones AppEngine application that uses Facebook for login."""

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

class Friends(webapp.RequestHandler):
    ''' Adicionamos amigos ao nosso amigo
    '''
    def post(self):
        limit = 40
        uid = self.request.get("user_id")
        user = FBUser.get_by_key_name(uid)
        fql = facebook.FQL(user.access_token)
        query ={"friends":
                    """SELECT uid,first_name,last_name,name,sex,birthday_date
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
                            uid1 IN (SELECT uid FROM #friends) 
                            AND uid2 in (SELECT uid FROM #friends)
                    """}
        try:
            friendsQuery,ffQuery = fql.multiquery(queries = query)
        except ValueError:
            logging.debug(fql.multiquery(queries = query))
            return ''
        friendsQuery = friendsQuery[u'fql_result_set']
        ffQuery = ffQuery[u'fql_result_set']
        tmpFF = {}
        for relation in ffQuery:
            uid1 = relation.get('uid1')
            uid2 = relation.get('uid2')
            if not str(uid1) in tmpFF:
                tmpFF[str(uid1)] = []
            tmpFF[str(uid1)].append(str(uid2))
        friends = []
        for friend in friendsQuery:
            friend['id'] = str(friend['uid'])
            friend['friends'] = tmpFF.get(str(friend['uid']),[])
            friends.append(friend)
        
        if friends:
            memcache.add(key="friends_%s" % str(user.id), value=friends, time=180)
        if tmpFF:
            memcache.add(key='queue_%s' % str(user.id),value=tmpFF,time=240)
        nUsers = len(friends)
        
        ranges = [(r,((((r+limit)<nUsers) and (r+limit)) or nUsers)) for r in range(0,nUsers,limit)]
        memcache.delete(key='queues_%s' % str(user.id))   
        tmpQueues = []
        for s,e in ranges:
            tmpQueues.append((s,e))
            logging.debug('Adiciona tarefa na fila %d - %d' % (s,e))
            taskqueue.add(queue_name='friendsUp' ,url='/queue/friend_fetch', params={'user_id':user.id,
                                                                               'start':s,
                                                                               'end':e,})
        memcache.add(key='queues_%s' % str(user.id),value=tmpQueues,time=180)                                                                       

class QueueFriends(webapp.RequestHandler):
    def post(self):
        limit = 100
        user_id = self.request.get("user_id")
        logging.debug('QueueFriends Start')
        data = memcache.get('queue_%s' % str(user_id))
        if not data:
            return ''
        users = FBUser.get_by_key_name(data.keys())
        nUsers = len(users)
        dictUsers = dict([(u.id,u.key()) for u in users])
        ranges = [(r,((((r+limit)<nUsers) and (r+limit)) or nUsers)) for r in range(0,nUsers,limit)]
        for s,e in ranges:
            tmpUsers = []
            for user in users[s:e]:
                actualFriends = user.friends
                newFriends = [dictUsers.get(uid,None) for uid in data[user.id] if not(dictUsers.get(uid,None) in actualFriends)]
                actualFriends.extend([k for k in newFriends if k])
                if actualFriends:
                    user.friends = actualFriends
                tmpUsers.append(user)
            db.put(tmpUsers)
        memcache.delete('queue_%s' % str(user_id))
        
class FriendsFetcher(webapp.RequestHandler):
    last = 0
    def post(self):
        uid = self.request.get("user_id")
        start = self.request.get("start",0)
        end = self.request.get("end",0)
        user = FBUser.get_by_key_name(uid)
        logging.debug('User ID (%s) Start (%s) End(%s)' % (str(user.id),str(start),str(end)))
        data = memcache.get('friends_%s' % str(user.id))
        if not data:
            graph = facebook.GraphAPI(user.access_token)
            friends = graph.get_connections(user.id, "friends")
            friends = friends.get('data',[])
        else:
            friends = data
        try:
            friends = self._storeFriends(friends,int(start),int(end),user.key())
            actualFriends = user.friends
            friends = [f.key() for f in friends if f.key() not in actualFriends]
            actualFriends.extend(friends)
            user.friends = actualFriends
            user.put()
        except DeadlineExceededError:
            self.response.clear()
            self.response.set_status(500)
            self.response.out.write("This operation could not be completed in time...")
        finally:
            queues = memcache.get('queues_%s' % str(user.id))
            queues.remove((int(start),int(end)))
            if queues:
                # Ainda temos uma fila?
                memcache.replace('queues_%s' % str(user.id),queues)
            else:
                logging.debug('Adding friendsFriendsUp')
                taskqueue.add(queue_name='friendsFriendsUp' ,url='/queue/queueFriends', params={'user_id':user.id,})
        
    
    def _storeFriends(self,friends,start=0,end=300,user_key=None):
        ''' Store friends as User objects
        '''
        users = []
        for friend in friends[start:end]:
            bFriends = [str(uid) for uid in friend.get('friends',user_key)] #user_key and [user_key,] or []
            fId = str(friend.get('id',friend.get('uid')))
            fName = friend.get('name')
            fFirstName = friend.get('first_name')
            fLastName = friend.get('last_name')
            fBirthday = friend.get('birthday_date')
            fSex = friend.get('sex')
            profile = {'id':fId,
                       'name':fName,
                       'first_name':fFirstName,
                       'last_name':fLastName,
                       'birthday':fBirthday,
                       'gender':fSex}
            user = FBUser.get_or_insert(key_name=str(fId),**profile)
            for k,v in profile.items():
                value = getattr(user,k)
                if v and not(v==value):
                    setattr(user,k,v)
            users.append(user)
        db.put(users)
        return users


def main():
    util.run_wsgi_app(webapp.WSGIApplication([(r"/queue/friend_fetch", FriendsFetcher),
                                              (r"/queue/getFriends", Friends),
                                              (r"/queue/queueFriends", QueueFriends),
                                             ]))


if __name__ == "__main__":
    main()
