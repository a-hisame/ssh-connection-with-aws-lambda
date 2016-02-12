#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import os
import uuid
import json
import codecs
import shutil
import logging
import datetime

import boto3
import fabric.api as fab

logger = logging.getLogger()
logger.setLevel(logging.INFO)

#logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

def _config():
  try:
    with codecs.open('config.json', 'r') as fh:
      return json.load(fh)
  except Exception as e:
    logger.exception(e)
    return None

conf = _config()

def _get_key():
  ''' SSHキーをダウンロードし、そのパスを返します '''
  # ssh接続時はパーミッションが関係するため、その準備
  keylocation = conf.get('Login', {}).get('KeyLocation')
  os.makedirs(keylocation)
  os.chmod(keylocation, 0700)
  
  # ローカルに落とす
  keypath = os.path.join(keylocation, 'id_rsa')
  bucket = conf.get('Login', {}).get('Bucket')
  key = conf.get('Login', {}).get('Key')
  boto3.resource('s3').meta.client.download_file(bucket, key, keypath)
  os.chmod(keypath, 0700)
  
  return keypath


def _init_fabric(keypath):
  ''' Fabric用のSSH設定を実施 '''
  login = conf.get('Login', {})
  fab.env.host_string = login.get('Hostname')
  fab.env.hosts = [login.get('Hostname')]
  fab.env.key_filename = [keypath]
  fab.env.user = login.get('User')
  fab.env.default_port = login.get('Port', 22)


def _gen_s3key(s3info, filename):
  ''' S3にアップロードするKey名を生成して返す '''
  prefix = s3info.get('Prefix', '')
  if s3info.get('DatePrefix', False):
    dt = datetime.datetime.utcnow()
    prefix = u'{0}/{1}'.format(prefix, dt.strftime('%Y/%m/%d'))
  return u'{0}/{1}'.format(prefix, filename)


def _finalize():
  ''' 不要な情報を全て削除する '''
  keylocation = conf.get('Login', {}).get('KeyLocation')
  if os.path.exists(keylocation):
    shutil.rmtree(keylocation)


def main(event, context):
  logger.info('START')
  try:
    collector = conf.get('Collector')
    if collector is None:
      logger.info('No Collector')
      return 'No Collector'
    
    # 対象のセットアップ
    _init_fabric(_get_key())
    # 事前処理を実行
    for command in collector.get('CreateCommands', []):
      logger.info(command)
      fab.run(command)
    
    # 事後処理(ログファイルをここのローカルにコピーしてS3にアップ)
    s3info = collector.get('S3')
    for remotefile in collector.get('TargetFiles', []):
      filename = os.path.basename(remotefile)
      localfile = '/tmp/{0}.log'.format(uuid.uuid4())
      fab.get(remote_path=remotefile, local_path=localfile)
      boto3.resource('s3').meta.client.upload_file(localfile, s3info.get('Bucket'), _gen_s3key(s3info, filename))
    
  finally:
    _finalize()

if __name__ == '__main__':
  main({}, {})

