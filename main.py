"""
Copyright 2014 Google Inc. All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import jinja2
import json
import logging
import time
import webapp2
import urllib
import util

from collections import OrderedDict
from google.appengine.api import users
from google.appengine.api import urlfetch
from google.appengine.api.logservice import logservice
from google.appengine.ext import ndb

from model import Feature
from model import FeatureMetadata2
from pipeline import PipelineImportData


JINJA_ENVIRONMENT = jinja2.Environment(
  loader=jinja2.FileSystemLoader("templates"),
  autoescape=True,
  extensions=["jinja2.ext.autoescape"])

class MainHandler(webapp2.RequestHandler):
  """The main page."""

  def get(self):
    user = users.get_current_user()
    #FeatureMetadata.get_or_insert("foo2")
    if user:
      samples = self._get_all_distinct_samples()
      features = self._get_all_distinct_features()
      self._render_page(samples, features, "sample", "feature")
    else:
      template = JINJA_ENVIRONMENT.get_template("grantaccess.html")
      self.response.write(template.render({
        "url": users.create_login_url("/")
      }))

  def post(self):
    # Render the page.
    samples = self._get_all_distinct_samples()
    features = self._get_all_distinct_features()
    lookupSample = str(self.request.get("lookupSample"))
    lookupFeature = str(self.request.get("lookupFeature"))
    lookupValue = None
    lookupResults = None
    if self.request.get("submitSampleFeature"):
      lookupValue = self._get_value_by_sample_feature(lookupSample, lookupFeature)
    if self.request.get("submitFeature"):
      lookupResults = self._get_results_by_feature(lookupFeature)
    if self.request.get("submitImport"):
      filename = str(self.request.get("importFilename"))
      blob_key = util.get_blob_key_from_file(filename)
      pipeline = PipelineImportData([blob_key], 100)
      pipeline.start()
      self.redirect('%s/status?root=%s' %
                    (pipeline.base_path, pipeline.pipeline_id))
    self._render_page(samples, features, lookupSample, lookupFeature,
                      lookupValue, lookupResults)

  def _render_page(self, samples, features, lookupSample, lookupFeature,
                   lookupValue=None, lookupResults=None):
    username = users.User().nickname()
    template = JINJA_ENVIRONMENT.get_template("index.html")
    self.response.out.write(template.render({
      "samples": samples,
      "features": features,
      "lookupSample": lookupSample,
      "lookupFeature": lookupFeature,
      "lookupValue": lookupValue,
      "lookupResults": lookupResults,
      "path": self.request.path,
      "username": username,
      "version": util.get_app_version(),
    }))

  def _get_all_distinct_samples(self):
    query = (Feature.query(projection=["sample"], distinct=True)
        .order(Feature.sample))
    features = query.fetch(100)
    samples = []
    for feature in features:
      samples.append(feature.sample)
    return samples

  def _get_all_distinct_features(self):
    query = (Feature.query(projection=["feature"], distinct=True)
        .order(Feature.feature))
    features = query.fetch(100)
    features_only = []
    for feature in features:
      features_only.append(feature.feature)
    return features_only

  def _get_value_by_sample_feature(self, sample, feature):
    query = Feature.query(Feature.sample == sample, Feature.feature == feature)
    features = query.fetch(1)
    value_only = "No value found for this sample and feature."
    for feature in features:
      value_only = feature.value
    return value_only

  def _get_results_by_feature(self, feature):
    query = Feature.query(Feature.feature == feature).order(Feature.sample)
    features = query.fetch(100)
    return features

# For demo purposes, map many sample pages to this handler.
app = webapp2.WSGIApplication(
  [
    ("/", MainHandler),
    ("/products", MainHandler),
    ("/purchase", MainHandler),
    ("/login", MainHandler),
    ("/contact", MainHandler),
  ],
  debug=True)

