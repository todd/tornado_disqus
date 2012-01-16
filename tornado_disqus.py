import logging, urllib
import tornado.auth

from tornado import escape
from tornado.httpclient import AsyncHTTPClient

class DisqusMixin(tornado.auth.OAuth2Mixin):
	# Mixin for authenticating and making API calls to Disqus
	_OAUTH_ACCESS_TOKEN_URL = "https://disqus.com/api/oauth/2.0/access_token/?"
	_OAUTH_AUTHORIZE_URL = "https://disqus.com/api/oauth/2.0/authorize/?"
	_OAUTH_NO_CALLBACKS = False
	
	def get_authenticated_user(self, redirect_uri, client_id, client_secret, code, callback):
		# Some comments here about usage
		http = AsyncHTTPClient()
		args = {
			"redirect_uri": redirect_uri,
			"code": code,
			"client_id": client_id,
			"client_secret": client_secret,
			"grant_type": "authorization_code"
			}
			
		fields = set(["id", "username", "name", "profileUrl", "email"])
								
		url = self._OAUTH_ACCESS_TOKEN_URL
		
		http.fetch(url, method = "POST", body = urllib.urlencode(args), 
			callback = self.async_callback(self._on_access_token, redirect_uri, client_id, client_secret,
			callback, fields))							
	
	def _on_access_token(self, redirect_uri, client_id, client_secret, callback, fields, response):
		if response.error:
			logging.warning("Disqus auth error: %s" % str(response))
			callback(None)
			return
			
		args = escape.json_decode(response.body)
		session = {
			"access_token": args["access_token"],
			"expires": args.get("expires")
			}
		
		self.disqus_request(
			path = "/users/details.json",
			callback = self.async_callback(
				self._on_user_details, callback, session, fields),
			access_token = session["access_token"],
			api_key = client_id
			)
		
	def _on_user_details(self, callback, session, fields, user):
		if user is None:
			callback(None)
			return
		
		fieldmap = {}
		for field in fields:
			fieldmap[field] = user.get("response").get(field)
			
		fieldmap.update({"access_token": session["access_token"], "session_expires": session.get("expires")})
		callback(fieldmap)
	
	def disqus_request(self, path, callback, access_token=None, post_args=None, **args):
		# Some stuff about request usage here
		url = "https://disqus.com/api/3.0" + path
		all_args = {}
		if access_token:
			all_args["access_token"] = access_token
			all_args.update(args)
			all_args.update(post_args or {})
		if all_args:
			url += "?" + urllib.urlencode(all_args)
		callback = self.async_callback(self._on_disqus_request, callback)
		http = AsyncHTTPClient()
		if post_args is not None:
			http.fetch(url, method="POST", body=urllib.urlencode(post_args), callback=callback)
		else:
			http.fetch(url, callback=callback)
			
	def _on_disqus_request(self, callback, response):
		if response.error:
			logging.warning("Error - response %s fetching %s" % (response.error, response.request.url))
			callback(None)
			return
		callback(escape.json_decode(response.body))
