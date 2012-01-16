import os.path, logging

import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.options

from tornado.options import options, define
from tornado.web import authenticated, asynchronous, RequestHandler, Application, HTTPError

from tornado_disqus import DisqusMixin

define("disqus_consumer_key", default="keygoeshere")
define("disqus_consumer_secret", default="keygoeshere")
define("port", default=8888, type=int)

class BaseHandler(RequestHandler):
	def get_current_user(self):
		if self.get_secure_cookie("user"):
			return tornado.escape.json_decode(self.get_secure_cookie("user"))
		return None
		
# Example usage of the disqus_request method
# This API call retrieves a list of posts made by the user and displays them.
class MainHandler(BaseHandler, DisqusMixin):
	@authenticated
	@asynchronous
	def get(self):
		self.disqus_request("/users/listPosts.json", self._on_posts, access_token=self.current_user["access_token"],
			api_key = options.disqus_consumer_key)
		
	def _on_posts(self, posts):
		if posts is None:
			self.redirect("/login")
			return
		self.render("index.html", posts=posts["response"])
		
# Example usage of the get_authenticated_user method
# This class, obviously, handles logging the user in to Disqus
class AuthLoginHandler(BaseHandler, DisqusMixin):
	@asynchronous
	def get(self):
		redirect = (self.request.protocol + "://" + self.request.host + "/login?next=/")
		if self.get_argument("code", False):
			self.get_authenticated_user(
				redirect_uri = redirect,
				client_id = self.settings["disqus_consumer_key"],
				client_secret = self.settings["disqus_consumer_secret"],
				code = self.get_argument("code"),
				callback = self._on_auth
			)
			return
		self.authorize_redirect(redirect_uri = redirect, client_id = self.settings["disqus_consumer_key"], 
			extra_params = {"response_type": "code", "scope": "read,write"})
		
	def _on_auth(self, user):
		if not user:
			raise HTTPError(500, "Disqus auth failed.")
		self.set_secure_cookie("user", tornado.escape.json_encode(user))
		self.redirect(self.get_argument("next", "/"))
		
class AuthLogoutHandler(BaseHandler, DisqusMixin):
	def get(self):
		self.clear_cookie("user")
		self.redirect(self.get_argument("next", "/"))
		
class App(Application):
	def __init__(self):
		handlers = [
			(r"/", MainHandler),
			(r"/login", AuthLoginHandler),
			(r"/logout", AuthLogoutHandler)
		]
		
		settings = dict(
			cookie_secret = "lg8QenRgQDq/QF1Ff2b+jwjN0PhqRUBiild1H+wSdoI=",
			login_url = "/login",
			template_path = os.path.join(os.path.dirname(__file__), "templates"),
			xsrf_cookies = True,
			disqus_consumer_key = options.disqus_consumer_key,
			disqus_consumer_secret = options.disqus_consumer_secret,
			debug = True,
			autoescape = None
		)
		
		Application.__init__(self, handlers, **settings)

def main():
	tornado.options.parse_command_line()
	http_server = tornado.httpserver.HTTPServer(App())
	http_server.listen(options.port)
	logging.warning("Tornado server now running on port %d" % options.port)
	tornado.ioloop.IOLoop.instance().start()
	
if __name__ == "__main__":
	main()