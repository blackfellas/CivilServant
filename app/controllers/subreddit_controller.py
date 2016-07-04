import praw
import inspect, os, sys # set the BASE_DIR
import simplejson as json
import datetime
import reddit.connection
import reddit.praw_utils as praw_utils
import reddit.queries
from utils.common import PageType
from app.models import Base, SubredditPage, Subreddit, Post

class SubredditPageController:
  def __init__(self, subname, db_session, r, log):
    self.subname = subname
    self.db_session = db_session
    self.log = log
    self.r = r    

  def fetch_subreddit_page(self, pg_type, limit=100):
      posts = []
      fetched = []
      sub = self.r.get_subreddit(self.subname)

      # fetch subreddit posts from reddit
      try:
          if pg_type==PageType.TOP:
              fetched = sub.get_top(limit=limit)
          elif pg_type==PageType.CONTR:
              fetched = sub.get_controversial(limit=limit)
          elif pg_type==PageType.NEW:
              fetched = sub.get_new(limit=limit)   
          elif pg_type==PageType.HOT:
              fetched = sub.get_hot(limit=limit)   
      except:
          self.log.error("Error querying /r/{0} {1} page".format(self.subname, pg_type.name), extra=sys.exc_info()[0] )
          print(sys.exc.info()[0])
          return []         
      self.log.info("Queried /r/{0} {1} page".format(self.subname, pg_type.name))

      # add sub to subreddit table if not already there
      try:
          self.archive_subreddit(sub)
          self.log.info("Saved new record for subreddit /r/{0}".format(self.subname))
      except:
          self.log.error("Failed to save new record for subreddit /r/{0}".format(self.subname), extra=sys.exc_info()[0] )

      # save subreddit posts to database
      try:
          for post in fetched:
              new_post = post.json_dict if("json_dict" in dir(post)) else post ### TO HANDLE TEST FIXTURES
              posts.append(new_post)
              self.archive_post(new_post)
          self.log.info("Saved posts from /r/{0} {1} page.".format(self.subname, pg_type.name))
      except:
          self.log.error("Error Saving posts from /r/{0} {1} page".format(self.subname, pg_type.name), extra=sys.exc_info()[0] )
              
      return posts

  def archive_subreddit_page(self, pg_type=PageType.HOT):
      posts = self.fetch_subreddit_page(pg_type)
      subreddit_page = SubredditPage(created_at = datetime.datetime.now(),
                             page_type = pg_type.value, 
                             page_data = json.dumps(posts))
      self.db_session.add(subreddit_page)
      self.db_session.commit()


  def archive_subreddit(self, sub):
      # TODO: should you even be allowed to archive a different subreddit than the one sp was made for?  
      sub_count = self.db_session.query(Subreddit).filter(Subreddit.id == sub.id).count()

      # if sub not in table, add it
      if sub_count == 0:
          new_sub = Subreddit(id = sub.id, 
                              name = sub.display_name)
          self.db_session.add(new_sub)
          self.db_session.commit()
      # else don't add it to subreddit table

  def archive_post(self, post):
      # note that 'post' is of type dictionary (has already been initially processed in fetch_subreddit_page)
      # TODO: carefully describe what the types of these 'archive' method args should be...
      post_count = self.db_session.query(Post).filter(Post.id == post['id']).count()

      # if sub not in table, add it
      if post_count == 0:
          new_post = Post(
                  id = post['id'],
                  subreddit_id = post['subreddit_id'].strip("t5_"), # janky
                  created = datetime.datetime.fromtimestamp(post['created_utc']),
                  post_data = json.dumps(post))
          self.db_session.add(new_post)
          self.db_session.commit()
      # else don't add it to post table



