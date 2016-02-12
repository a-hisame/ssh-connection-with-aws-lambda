# S3 Data Collector with AWS Lambda

AWS Lambda にVPC内リソースへのアクセス機能が追加されましたが、
それを使って Lambda --> SSH --> Instance という処理が出来ないかの検証を行いました。

結果として成功したので、そのサンプルとしてInstance内のファイルをSSH経由で取得し、
S3にアップロードするというサンプルを置いておきます。

なお、SSH接続のためにfabricを利用しました。
コマンドとしての `/usr/bin/ssh` や `/bin/ping` は Lambda からアクセスできませんでした。


## 準備 (ローカル)

1. Amazon Linux上で以下のコマンドを実行し、依存関係のあるファイル類を取得し、
このプロジェクト内のlibs以下にコピーする。
2. `develops/config.json` を書き換える
3. `build.sh` を実行して main.zip を作る

```bash
# Amazon Linuxにログイン
sudo yum -y install autoconf python27-devel gcc
mkdir libs
cd libs
pip install fabric -t .

# これだけだと pycrypto がlibs内にインストールされないので、
# pycryptoがインストールされた別フォルダから値を取得する
cp -r /usr/local/lib64/python2.7/site-packages/Crypto .
cp -r /usr/local/lib64/python2.7/site-packages/Crypto/pycrypto-2.6.1.egg-info .

# リモートで実施した場合はローカルにコピーする、などをここで実施

# Lambda用のzipファイルを作る
cd ../
bash build.sh
```


## 準備 (AWS Lambda用設定)

* Functionを作る
* RuntimeはPython2.7を指定する
* ソースは上記で作成したmain.zipをアップロードする
* Handlerには `main.main` を指定する
* デフォルトで作られるIAM Roleに対して、追加で以下の権限が必要
  (SSH鍵をストアしているS3バケットへのs3:GetObject,
  結果をアップロードするS3バケットへのs3:PutObject,
  Lambda用のNetworkInterfaceを作るためのec2:CreateNetworkInterface)
* どのsubnet内でローンチするかを決定するが、このsubnet内のルートテーブルにS3に対するエンドポイント、
  あるいは、NATインスタンスへのルーティングが必要 (デフォルトでインターネットに出ない)
* ログの大きさにもよるが、十分小さければTimeoutは20秒ぐらいで十分
* "Test" を実行して動作を確認
* SSH接続に必要なSecurity Groupを用意して、Lambda Functionと接続対象にAttach

## 設定値

`src/config.json` ですが、今回はサンプルとして固定値を利用しています。
Lambdaの引数で与える改造などは好きに実施してください。

```javascript
{
	"Login": {
		"Bucket": "your-sample-bucket",
		"Key": "ssh-key/test",
		"User": "ec2-user",
		"Hostname": "192.168.1.10",
		"Port": 22,
		"KeyLocation": "/tmp/ssh"
	},
	"Collector": {
		// ファイルを回収する前にこのコマンドをssh経由で実行します
		// ここでは、/var/log 以下全てをzip圧縮しています
		"CreateCommands": [
			"sudo python -m zipfile -c /tmp/lambda-logs.zip /var/log/"
		],
		// どのファイルを回収するかを指定します
		// 同名の場合は基本上書きとなります
		"TargetFiles": [
			"/tmp/lambda-logs.zip"
		],
		// S3の何処にストアするかです
		// IAMロールを使用するため、一度Lambdaの実行端末上にファイルをコピーして持ってきます
		// DatePrefixがtrueの場合、 ${Prefix}/${yyyy}/${mm}/${dd}/ のようなPrefixが入ります
		// DataPrefixがfalseの場合、 ${Prefix}/ のみがPrefixとして利用されます
		"S3": {
			"Bucket": "your-sample-bucket",
			"Prefix": "lambda-collector",
			"DatePrefix": true
		}
	}
}
```

## LICENSES

以下のライブラリを利用しています。
このソフトウェア自体はMITライセンスで提供されます。

* boto3 - https://github.com/boto/boto3 (Apache 2.0)
* fabric - https://github.com/fabric/fabric (MIT)

ただし、fabricは内部でLGPLのparamikoを利用しています。

