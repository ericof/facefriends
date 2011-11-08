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
from google.appengine.ext.db import GqlQuery
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
from google.appengine.api import memcache

from models import FBUser
from models import FBGroup
from models import FBLocation
from models import FBEmployeer
from models import FBSchool
from models import FBWorkPosition
from models import FBSchoolEnroll

class BaseHandler(webapp.RequestHandler):
    ''' Base app handler
    '''
    
    def _userCount(self):
        ''' Retorna numero de usuarios cadastrados
        '''
        stats = memcache.get(key='APPStats')
        if not stats:
            stats = GqlQuery("SELECT __key__ FROM FBUser WHERE accessed = TRUE").count()
            memcache.add(key='APPStats',value=stats,time=240)
        return stats
    
    def show(self,templateName='index.html',args={}):
        ''' Base method for rendering templates
        '''
        base_path = os.path.join(os.path.dirname(__file__), "templates/")
        args['userCount'] = self._userCount()
        if not 'title' in args:
            args['title'] = u''
        # Retorna header
        path = os.path.join(base_path, "header.html")
        self.response.out.write(template.render(path, args))
        if not(templateName.find('/')>-1):
            path = os.path.join(base_path, templateName)
        else:
            # templateName eh um path
            path = templateName
        self.response.out.write(template.render(path, args))
        
        #Retorna Footer
        path = os.path.join(base_path, "footer.html")
        self.response.out.write(template.render(path, args))

class BaseFBHandler(BaseHandler):
    """Base Facebook app handler
    """
    @property
    def current_user(self):
        if not hasattr(self, "_current_user"):
            self._current_user = None
            self.cookie = facebook.get_user_from_cookie(self.request.cookies, FACEBOOK_APP_ID, FACEBOOK_APP_SECRET)
            if self.cookie:
                user = FBUser.get_by_key_name(self.cookie["uid"])
                graph = facebook.GraphAPI(self.cookie["access_token"])
                profile = graph.get_object("me")
                if not user:
                    user = self.createUser(accessed=True,profile=profile)
                    user.access_token = self.cookie["access_token"]
                elif user.access_token != self.cookie["access_token"]:
                    user.access_token = self.cookie["access_token"]
                self.updateUser(user,profile=profile)
                user.accessed = True
                user.put()
                self._current_user = user
        return self._current_user
    
    def createUser(self,accessed=False,profile={}):
        ''' Create a FBUser with at least id and name
        '''
        init={}
        init['key_name'] = profile.get('id')
        init['id'] = profile.get('id')
        init['name'] = profile.get('name')
        init['accessed'] = accessed
        user = FBUser(**init)
        return user
    
    def updateUser(self,user,profile={}):
        ''' Let's update this user
        '''
        base_properties = ['first_name','last_name','name','link','about','birthday',
                           'email','website','bio','quotes','gender',
                           'relationship_status', 'religion','political','timezone']
        list_properties = ['interested_in','meeting_for']
        geo_properties = ['hometown','location']
        for prop in base_properties:
            value = profile.get(prop)
            if hasattr(user,prop) and value:
                setattr(user,prop,value)
            
        # Update Hometown and Location               
        for prop in geo_properties:
            value = profile.get(prop)
            if hasattr(user,prop) and value:
                location = self._location(value.get('id'),value.get('name'))
                setattr(user,prop,location)
        
        if 'significant_other' in profile:
            fName = profile.get('significant_other')['name']
            fId = profile.get('significant_other')['id']
            profile = {'id':fId,'name':fName}
            user = FBUser.get_or_insert(key_name=str(fId),**profile)
            user.significant_other = tmpUser
    
    def getUserById(self,id):
        ''' Given a user_id we get a instance of FBUser
        '''
        return FBUser.get_by_key_name(id)
    
    def _location(self,id,name=''):
        location = FBLocation.get_by_key_name(id)
        if not location:
            location = FBLocation(key_name=id,
                                  id=id,
                                  name=name)
            location.put()
        return location
    
    def _employeer(self,id,name=""):
        employeer = FBEmployeer.get_by_key_name(id)
        if not employeer:
            employeer = FBEmployeer(key_name=id,
                                    id=id,
                                    name=name)
            employeer.put()
        return employeer
    

class HomeHandler(BaseFBHandler):
    ''' Handler for home page
    '''
    def friends(self):
        ''' Let's get the friends of this user
        '''
        user = self.current_user
        if user:
            taskqueue.add(url='/queue/getFriends', params={'user_id':user.id})
        
    
    def get(self):
        current_user = self.current_user
        args = dict(current_user=current_user,
                    facebook_app_id=FACEBOOK_APP_ID)
        self.friends()
        self.show(templateName='index.html',args=args)


def main():
    util.run_wsgi_app(webapp.WSGIApplication([
                                              (r"/", HomeHandler),
                                             ]))

if __name__ == "__main__":
    main()
