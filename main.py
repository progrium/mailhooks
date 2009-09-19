#!/usr/bin/env python

import wsgiref.handlers

from google.appengine.ext import webapp
from google.appengine.api import users
from google.appengine.ext.webapp import template
from google.appengine.ext import db
from google.appengine.api import urlfetch
from google.appengine.api import mail
import time, urllib, os

HOOKAH_URL = "http://hookah.progrium.com/dispatch"
PDROID_URL = "http://pdroid.progrium.com"
#PDROID_URL = "http://localhost:8080"
PDROID_TOKEN = 'j083y7huf852s44s4sx4s4++__'

def baseN(num,b,numerals="0123456789abcdefghijklmnopqrstuvwxyz"): 
    return ((num == 0) and  "0" ) or (baseN(num // b, b).lstrip("0") + numerals[num % b])

class MainHandler(webapp.RequestHandler):

    def get(self):
        user = users.get_current_user()
        if user:
            logout_url = users.create_logout_url("/")
            hooks = MailHook.all().filter('user =', user)
        else:
            login_url = users.create_login_url('/')
        self.response.out.write(template.render('templates/main.html', locals()))
    
    def post(self):
        if self.request.POST.get('name', None):
            h = MailHook.all().filter('name =', self.request.POST['name']).get()
            h.delete()
        else:
            h = MailHook(hook_url=self.request.POST['url'])
            h.put()
        self.redirect('/')

class ReflectorHandler(webapp.RequestHandler):
    def post(self):
        name = self.request.POST['to'].split('@')[0]
        hook = MailHook.all().filter('name =', name).get()
        self.redirect(hook.hook_url)

class ListenHandler(webapp.RequestHandler):
    def get(self):
        try:
            result = urlfetch.fetch(url='?'.join([os.path.join(PDROID_URL, 'smtp:listen:25'), str(abs(hash(time.time())))]))
            if not result.content == PDROID_TOKEN:
                resp = urlfetch.fetch(url=os.path.join(PDROID_URL, 'smtp:listen:25'), method='POST', 
                            payload=urllib.urlencode({'callback':'http://www.mailhooks.com/reflector', 'token': PDROID_TOKEN}))
                if not resp.status_code == 202:
                    mail.send_mail(
                        sender="MailHooks <robot@mailhooks.com>",
                        to="progrium@gmail.com",
                        subject="[MailHooks] Pdroid listen fail",
                        body=resp.content)
                    self.response.out.write(resp.content)
                else:
                    self.response.out.write("now listening")
            else:
                self.response.out.write("listening fine")
        except urlfetch.DownloadError, e:
            mail.send_mail(
                sender="MailHooks <robot@mailhooks.com>",
                to="progrium@gmail.com",
                subject="[MailHooks] Pdroid down?",
                body=str(e))
            self.response.out.write("Pdroid down")

class MailHook(db.Model):
    user = db.UserProperty(auto_current_user_add=True)
    hook_url = db.StringProperty(required=True)
    name = db.StringProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)
    
    def __init__(self, *args, **kwargs):
        kwargs['name'] = kwargs.get('name', baseN(abs(hash(time.time())), 36))
        super(MailHook, self).__init__(*args, **kwargs)

def main():
    application = webapp.WSGIApplication([('/', MainHandler), ('/reflector', ReflectorHandler), ('/listen', ListenHandler)], debug=True)
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
    main()
