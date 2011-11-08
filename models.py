#-*- code:utf-8 -*-

from google.appengine.ext import db
from geo.geomodel import GeoModel
from datetime import datetime

class BaseMetadata(db.Model):
    '''
    '''
    created = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)
    

class FBLocation(BaseMetadata,GeoModel):
    ''' A Facebook Location
    '''
    id = db.StringProperty(required=True)
    name = db.StringProperty(required=True)
    

class FBEmployeer(BaseMetadata):
    ''' A Facebook employeer reference  
    '''
    id = db.StringProperty(required=True)
    name = db.StringProperty(required=True)
    
    @property
    def alumni(self):
        positions = FBWorkPosition.gql("WHERE employeer = :1", self.key())
        return [e.user for e in positions]

class FBSchool(BaseMetadata):
    ''' A Facebook school reference
    '''
    id = db.StringProperty(required=True)
    name = db.StringProperty(required=True)
    
    @property
    def alumni(self):
        enrolls = FBSchoolEnroll.gql("WHERE school = :1", self.key())
        return [e.user for e in enrolls]
        

class FBWorkPosition(BaseMetadata):
    ''' A Facebook work position
    '''
    employeer = db.ReferenceProperty(FBEmployeer)
    location = db.ReferenceProperty(FBLocation)
    position = db.StringProperty(required=False)
    start_date = db.StringProperty(required=False)
    end_date = db.StringProperty(required=False)
    @property
    def user(self):
        return FBUser.gql("WHERE work = :1", self.key())

class FBSchoolEnroll(BaseMetadata):
    ''' A Facebook  school enrollment
    '''
    school = db.ReferenceProperty(FBSchool)
    year = db.StringProperty(required=False)
    
    @property
    def user(self):
        return FBUser.gql("WHERE education = :1", self.key())

class FBUser(BaseMetadata):
    ''' A Facebook user
    '''
    accessed = db.BooleanProperty(default=False)
    access_token = db.StringProperty(required=False)

    # # FBUserProperties
    id = db.StringProperty(required=True)
    first_name = db.StringProperty() # The user's first name
    last_name = db.StringProperty() # The user's last name
    name = db.StringProperty(required=True) # The user's full name
    link = db.LinkProperty() # A link to the user's profile
    about = db.TextProperty() # The user's blurb that appears under their profile picture
    birthday = db.StringProperty() # The user's birthday
    work = db.ListProperty(db.Key) # A list of the work history from the user's profile
    education = db.ListProperty(db.Key) # A list of the education history from the user's profile
    email = db.StringProperty() # The proxied or contact email address granted by the user
    website = db.LinkProperty() # A link to the user's personal website.
    hometown = db.ReferenceProperty(FBLocation,
                                    collection_name="user_hometown") # The user's hometown
    location = db.ReferenceProperty(FBLocation,
                                    collection_name="user_location") # The user's current location
    bio = db.TextProperty() # The user's bio
    quotes = db.TextProperty() # The user's favorite quotes
    gender = db.StringProperty() # The user's gender
    interested_in = db.StringListProperty() # Genders the user is interested in
    meeting_for = db.StringListProperty() # Types of relationships the user is seeking
    relationship_status = db.StringProperty() # The user's relationship status
    religion = db.StringProperty() # The user's religion
    political = db.StringProperty() # The user's political view
    verified = db.BooleanProperty() # The user's account verification status
    significant_other = db.SelfReferenceProperty() # The user's significant other
    timezone = db.IntegerProperty() # The user's timezone
    
    friends = db.ListProperty(db.Key) # List of Friends this user
    groups = db.ListProperty(db.Key) # List of groups this user

class FBGroup(BaseMetadata):
    ''' A Facebook Group
    '''
    id = db.StringProperty(required=True)
    owner = db.ReferenceProperty(FBUser)
    name = db.StringProperty(required=True)
    description = db.TextProperty()
    
    @property
    def members(self):
        return FBUser.gql("WHERE groups = :1", self.key())