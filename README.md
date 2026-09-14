# xr_teleoperate_all_in_one

Unitree 公式の実機 XR テレオペと Isaac Lab シミュレーションを、用途別の2つの Docker イメージで実行します。ビルド・起動は共通の Docker Compose で管理します。
シミュレーションは G1 29DoF + Dex3 / BrainCo Revo2。`docker/teleop.sh` は既定でコントローラーで腕と3指ハンドを操作します。`minimalist_compliance_control` は含めません。

Revo2の検証範囲・制限は下記「BrainCo Revo2」を参照してください。Questでの操作・把持確認は利用環境で行ってください。

## 依存構成

トップレベルのソース依存は次の5つです。`xr_teleoperate/` と `unitree_sim_isaaclab/` は通常のフォルダとして取り込み、このリポジトリでコードと変更履歴を直接管理します。残り3つは [docker/repos.lock](docker/repos.lock) に公式コミットを固定し、Docker ビルド時にイメージ内の `/opt/src/` 以下へ取得します。

このリポジトリに Git submodule は登録しません。XR の元コミット・ライセンス・取り込み時の差分は [UPSTREAM.md](xr_teleoperate/UPSTREAM.md) に記録しています。

| リポジトリ | 役割 |
| --- | --- |
| [cyclonedds](https://github.com/eclipse-cyclonedds/cyclonedds) | SDK が使う DDS の C ライブラリ。`releases/0.10.x` 系 |
| [IsaacLab](https://github.com/isaac-sim/IsaacLab) | シミュレーションフレームワーク。Unitree の 5.1 手順に記載されたコミット |
| [unitree_sdk2_python](https://github.com/unitreerobotics/unitree_sdk2_python) | シミュレーション・実機との DDS 通信 |
| [unitree_sim_isaaclab](https://github.com/unitreerobotics/unitree_sim_isaaclab) | Unitree のロボット・タスク・シミュレーション |
| [xr_teleoperate](https://github.com/unitreerobotics/xr_teleoperate) | XR 入力、逆運動学、テレオペ、記録 |

これに加えて、次もイメージ内に必要です。

- **Isaac Sim 5.1.0**: NVIDIA の pip 配布からインストールします。ソースリポジトリの clone は不要です。
- **televuer / teleimager / dex-retargeting**: 公式 XR が指定する版を [docker/repos.lock](docker/repos.lock) に固定し、他の依存と一緒に `/opt/src/` へ取得します。編集用の `/opt/src/xr_teleoperate/` の外に置くので、bind mount しても依存を隠しません。`dex-retargeting` は公式 XR が参照する `silencht` 版です。
- **シミュレーション用 teleimager**: 元の指定版 `b81de448…` を `/opt/src/sim-teleimager` に別途取得し、XR側とは別環境にインストールします。
- **実機カメラの画像配信**: XR 環境に `teleimager[server]` と、Ubuntu 22.04 用の `libusb-1.0-0-dev`・`libturbojpeg0-dev` をインストールします。
- **USD・モデル等のアセット**: 公式の `fetch_assets.sh` で [Unitree の Hugging Face データセット](https://huggingface.co/datasets/unitreerobotics/unitree_sim_isaaclab_usds) から取得します。

| Compose サービス | イメージ | Python 環境・用途 |
| --- | --- | --- |
| `xr` | `xr-teleoperate-all-in-one:teleop` | `tv`（Python 3.10 / Pinocchio 3.1.0 / NumPy 1.26.4）。テレオペ・記録 |
| `sim` | `xr-teleoperate-all-in-one:sim-isaac5.1` | `unitree_sim_env`（Python 3.11 / Isaac Sim 5.1）。シミュレーション・画像配信 |
| `image-server` | `xr` と同じテレオペ用イメージ | 実機カメラの画像配信 |

各プロセスを別コンテナで起動し、host network で通信します。テレオペ用イメージには Isaac Sim・IsaacLab・Sim assets・Revo2 のシミュレーション用モデルを含めません。実機操作だけなら `sim` のビルド・起動は不要です。

## ビルド

ビルドする PC は Linux x86_64、Docker Engine、Docker Compose が必要です。`sim` と `xr` サービスの実行には、従来どおり NVIDIA GPU、対応ドライバ、NVIDIA Container Toolkit も必要です。XR の GPU・描画設定と既存の依存は維持し、今回はイメージの分割だけを行います。画像配信用の `image-server` は従来どおり GPU を要求しません。Python / CUDA Toolkit / Conda のホストへのインストールは不要です。GPU とドライバの条件は [Isaac Sim 5.1 の要件](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/installation/requirements.html) を確認してください。

Docker 関連のファイルは `docker/` にまとめています。以降の Docker コマンドは `docker/` 内で実行します。

```bash
cd docker
docker compose build
```

上記で両イメージをビルドします。必要な用途だけビルドすることもできます。

```bash
docker compose build xr            # テレオペだけ（Isaac・Sim assets の取得なし）
docker compose build sim           # シミュレーションだけ
docker compose build image-server  # カメラPC用。xr と同じイメージ
```

従来の `docker compose build xr` は、分割後はテレオペ用だけのビルドになります。

ビルドコンテキストはリポジトリ全体ですが、各対象が必要なソースだけをコピーします。既存の `docker/Dockerfile` 内で共通部分から `teleop`・`sim` の2対象に分岐し、除外設定は `docker/Dockerfile.dockerignore` を使います。

XR 用の証明書と秘密鍵も、テレオペ用イメージのビルド中に準備します。既存の `g1_xr_teleop_admittance` の Dockerfile と同じく、取得した televuer に `cert.pem` と `key.pem` があればコピーし、なければ OpenSSL で自己署名証明書と秘密鍵を生成します。保存先はイメージ内の `/root/.config/xr_teleoperate/` です。Sim 用 teleimager の固定版には証明書が同梱されていないため、Sim 用イメージでも同じ OpenSSL コマンドで同じ保存先に準備します。

Dockerfile 内で `docker/repos.lock` を読み、共通依存と各用途に必要な依存を、それぞれのビルド段階でイメージ内の `/opt/src/` へ取得します。各依存が必要とする submodule もそこで初期化します。利用者による別スクリプトの実行は不要です。編集用の XR・シミュレータ本体は、ホストの通常ファイルを `COPY` でイメージに含めます。

新しい環境では、このリポジトリを通常どおり clone すれば XR のコード・ロボットモデルも揃います。submodule の初期化や、ホストへの依存リポジトリの clone は不要です。Git LFS は Docker 内のアセット取得に使用します。

ビルドにはネットワーク接続と十分なディスク容量が必要です。Sim 用は Isaac Sim、PyTorch、USD アセットを含むため大きなイメージになります。旧イメージ・キャッシュ・記録データは自動削除しません。GPU に依存する動作確認は実行時に行います。

分割後の両イメージのビルド、XR の主要依存・CLI、BrainCo DDS テスト4件、既存のBrainCo物理回帰テストを確認しました。Dex3・Revo2のカメラ付き起動と、別イメージのXRによるDDS接続・480×640画像受信・記録処理の初期化も確認済みです。Questでの追従・把持・記録データの収集と実機操作は未確認です。既存G1の脚の振動は今回の分割では変更していません。

## シミュレーションと XR の起動

```bash
cp .env.example .env
```

作成した `docker/.env` の `IMG_SERVER_IP` を XR ヘッドセットから到達できる画像サーバー PC の LAN IPv4 に変更します。通常はシミュレーションを動かすこの PC のアドレスです。`127.0.0.1` のままでは外部の XR ヘッドセットから接続できません。

ターミナル1（`docker/` 内）:

```bash
docker compose run --rm sim sim
```

シミュレーションと画像サービスが起動したら、ターミナル2（同じく `docker/` 内）:

```bash
./teleop.sh
```

`teleop.sh` はコントローラー・G1_29・Dex3・記録機能有効で起動します。設定はスクリプト内の Python 起動引数を直接編集します。画像サーバー IP と NIC は既存の `.env` を使い、再ビルドは不要です。素手で Dex3 も操作する場合は、従来の `docker compose run --rm xr teleop --record` を使います。

デスクトップのターミナルから起動すると、X11の画面設定・認証をコンテナへ渡し、記録中のRerunグラフを表示します。

左右それぞれのコントローラーで、同じ側のハンドを操作します。

- トリガー：人差し指と親指でつまみます。中指は開いたままです。
- グリップ：中指と親指でつまみます。人差し指は開いたままです。
- 両方：押し込み量に応じて深い握り込みへ連続的に変わります。両方を押し切ると、人差し指・中指はモデル上の上限（根元90°・指先100°）まで曲がります。
- 離す：押し込み量に応じて開きます。

指の目標角度はモデルの指先位置から求めた姿勢を補間し、変化速度を最大4 rad/sに制限します。接触を検出して止める力制御ではありません。実物での指先の合い方は未確認です。調整する場合は `robot_hand_unitree.py` の `dex3_controller_targets` 内の姿勢を編集します。

記録形式は従来どおり、`states` に左右各7関節の実際の角度、`actions` に速度制限後の目標角度を保存します。コントローラーの押し込み量そのものは保存しません。

ヘッドセットのブラウザで画像サービス `https://<PCのLAN IP>:60001`、続いて XR UI `https://<PCのLAN IP>:8012/?ws=wss://<PCのLAN IP>:8012` を開きます。初回は自己署名証明書を信頼する操作が必要です。端末側の具体的な設定は [公式 XR 手順](https://github.com/unitreerobotics/xr_teleoperate#21--environment-setup) に従ってください。

ターミナルで `r` が操作開始、`s` が記録開始 / 保存、`q` が終了です。公式の既定保存先 `xr_teleoperate/teleop/utils/data/` にホストの `data/` を接続しています。現構成ではコンテナは root で動くため、保存ファイルも root 所有になります。

シミュレーションは `--headless --enable_cameras` で画面なしのカメラ描画を行います。公式ソースの `--no_render` は描画更新を止めるため、既定では使いません。DDS は XR の `--sim` による domain 1 を使い、NIC は双方で自動選択します。複数 NIC がある場合は、シミュレーション側の選択に合わせて `docker/.env` の `NETWORK_INTERFACE` を指定してください。

テレオペと Sim の画像配信は、それぞれのイメージのビルド時に準備した証明書を使います。追加の証明書作成コマンドは不要です。証明書の再発行や Apple Vision Pro 用 CA 証明書の導入が必要な場合は、公式手順に沿って設定してください。

## 実機での起動

`docker/.env` の `IMG_SERVER_IP` を画像サーバーの IP、`NETWORK_INTERFACE` を実機と接続している NIC 名に設定します。画像サーバーが G1 の PC2 など別 PC で動いている場合は、その IP を指定します。

```bash
./teleop-real.sh
```

`teleop-real.sh` は G1_29 の両腕をコントローラーで操作し、記録機能も有効にします。`--sim` と `--ee` を付けず、実機用 DDS domain 0 を使います。3指ハンドの通信は待ちません。`r` で操作開始、`s` で記録開始・保存です。腕以外の関節は公式の既存処理で姿勢を保持します。

スクリプト内の起動引数を直接編集でき、再ビルドは不要です。既存の `docker compose run --rm xr teleop-real` は素手・Dex3用のままなので、腕だけのコントローラー操作には `teleop-real.sh` を使ってください。保存先と保存ファイルの所有者設定は変更していません。

`teleop-real.sh` は `DISPLAY` と既存のX11認証ファイル（`XAUTHORITY`、未指定なら `~/.Xauthority`）をコンテナへ渡し、Rerunをホストの画面に表示します。デスクトップのターミナルから起動してください。記録中は左右の腕の実際の角度・目標角度を表示します。

このイメージは Linux x86_64 向けです。画像サーバーは、このリポジトリをクローンした別の x86_64 PC でも実行できます。ARM の PC2 にそのまま配置する構成ではありません。ARM 側で画像を配信する場合は、その機種に適した公式 teleimager の環境を使用します。

## カメラを接続した PC での画像配信

画像を配信する PC にこのリポジトリをクローンし、その PC の `docker/` 内で `docker compose build image-server` と以下の操作を行います。テレオペと同じ PC でも別 PC でも構いません。既に画像サーバーが動いている場合は追加起動は不要です。

既存の Docker 起動スクリプトと同じ動画・USB デバイスのアクセス許可を設定しています。使うデバイスを起動時に指定します。以下は `/dev/video0` と `/dev/bus/usb` が存在する場合の例です。複数の OpenCV カメラを使う場合は、必要な `/dev/videoN` の `-v` を追加してください。

```bash
docker compose run --rm \
  -v /dev/video0:/dev/video0 \
  -v /dev/bus/usb:/dev/bus/usb \
  image-server image-server-cf
```

公式の設定ファイルを `docker/` に取り出します。このコマンドは初回に実行します。

```bash
docker compose run --rm -T image-server shell -c \
  'cat /opt/src/teleimager/cam_config_server.yaml' > cam_config_server.yaml
```

カメラ検出結果に合わせて `cam_config_server.yaml` の `type`、`video_id` / `serial_number`、解像度を編集し、使わないカメラは `enable_zmq` と `enable_webrtc` を両方 false にします。設定項目は [公式 teleimager の README](https://github.com/unitreerobotics/teleimager) に従います。

```bash
docker compose run --rm \
  -v /dev/video0:/dev/video0 \
  -v /dev/bus/usb:/dev/bus/usb \
  -v "$PWD/cam_config_server.yaml:/opt/src/teleimager/cam_config_server.yaml:ro" \
  image-server
```

画像配信が起動したら、テレオペ側 PC の `docker/.env` の `IMG_SERVER_IP` を配信 PC の LAN IP に合わせ、`teleop-real` を起動します。同じ PC でシミュレーションの画像サーバーと実機カメラの画像サーバーを同時起動すると既定ポートが重なるため、使用する側を起動してください。RealSense の専用ドライバや追加ハンド用サービスは、使用する機材に合わせて別途設定が必要です。

## 開発用シェル

```bash
docker compose run --rm xr shell      # tv / xr_teleoperate/teleop
docker compose run --rm sim sim-shell  # unitree_sim_env / unitree_sim_isaaclab
```

## xr_teleoperate の変更

ホストの `xr_teleoperate/` をコンテナの `/opt/src/xr_teleoperate/` に bind mount しています。編集するのは、例えば `xr_teleoperate/teleop/teleop_hand_and_arm.py` や `xr_teleoperate/teleop/robot_control/robot_arm.py` です。

- Python コードの変更: ファイルを保存し、実行中の teleop を終了して起動し直します。Docker の再ビルドは不要です。
- Python 依存や `docker/repos.lock` の版の変更: `docker compose build` で環境を作り直します。
- `unitree_sim_isaaclab/` の編集対象コードも Sim コンテナへ bind mount します。その他の依存はイメージ内の固定版を使用します。

変更の保存は、このリポジトリだけで完結します。以下は利用者がリポジトリ直下で変更内容を確認して実行する例です。

```bash
git diff -- xr_teleoperate
git add xr_teleoperate/teleop/robot_control/robot_arm.py  # 変更したファイルを選択
git commit -m "Update XR arm control"
git push
```

初回は同梱した `xr_teleoperate/` 全体と Docker 設定も、このリポジトリへの追加対象です。別の XR 用リモートリポジトリを用意する必要はありません。公式の履歴は同梱していないため、上流との比較には `UPSTREAM.md` の元コミットを使います。

## 骨格の範囲と残作業

既存 Docker 構成と公式ソースを照合し、次のように揃えています。

| 項目 | 採用した処理 |
| --- | --- |
| Conda・Python 環境 | 既存と同じ Miniconda、シミュレーション用 Python 3.11 と XR 用 Python 3.10 |
| 起動時の同意設定 | 既存と同じ `ACCEPT_EULA=Y`・`PRIVACY_CONSENT=Y`。独自の起動前チェックは追加しない |
| 画像サーバーの指定 | 既存と同じ `IMG_SERVER_IP`、DDS は `NETWORK_INTERFACE` |
| シミュレーションのカメラ設定 | 公式手順の `type: isaacsim`・`image_shape: [480, 640]` を既存と同じ sed で設定 |
| GPU・共有メモリ | 既存と同じ GPU 公開、host network / IPC、ulimit、Vulkan ICD の読み取り専用マウント |
| XR 起動 | 公式の引数を使用。現行公式の Dex3 に合わせて `--input-mode hand`。画面なしで使うため `--headless` |
| 記録 | 公式の既定保存先をホストの `data/` に接続 |

`entrypoint.sh` は、既存の起動スクリプトと同様に Conda 環境・作業ディレクトリを選んで公式コマンドを起動する部分だけです。ソースの取得・XR の編集用マウント・アセットのビルド時取得は、この all-in-one 構成のための処理です。

PyTorch は固定した公式 IsaacLab が選ぶ `2.7.0 / cu128` を使用します。シミュレーション用の Pinocchio は既存と同じく IsaacLab の依存として pip で導入します。この環境に Conda 版 Pinocchio 3.1.0 を追加すると Isaac Sim の USD 読み込みと衝突するため、Conda 版は XR 環境だけに入れます。既存の `params-proto==2.13.0` も Dockerfile 内に維持しています。既存の `pip --force-reinstall --no-deps` によるパッケージ上書きは、今の依存構成で必要か未確認のため追加していません。

- 公式版では `--input-mode` を使用し、Dex3 は hand 入力のみです。旧環境の `--xr-mode controller --ee dex3` は引き継ぎません。
- 実機用の起動と UVC / OpenCV カメラの画像配信手順を用意しています。カメラの具体的な設定・追加ハンド用サービスは使用する機材に合わせて設定します。
- 依存は `docker/repos.lock`、XR・シミュレータ本体はこのリポジトリの通常ファイルとして管理します。ビルドには作業ツリーの未コミット変更も含まれます。アセット取得先の revision、OS / Python の全推移依存まではロックしていません。
- Docker イメージのビルド、XR の主要モジュール・UVC の import、既定タスクのロボット・テーブルの USD と証明書の配置を確認済みです。シミュレーション環境の修正後、Pinocchio を読み込んだ状態での Isaac Sim の GPU 起動、`Sdf.TokenListOp` の操作、USD ステージの作成も確認しました。両環境の依存整合性全体、タスクを通したシミュレーション、実機カメラの検出・配信、XR 映像・操作・記録は未確認です。実機への指令送信はまだ行っていません。

参照: [公式の Isaac Sim 5.1 導入手順](https://github.com/unitreerobotics/unitree_sim_isaaclab/blob/main/doc/isaacsim5.1_install.md)、[公式 XR 導入手順](https://github.com/unitreerobotics/xr_teleoperate)、[公式 submodule 定義](https://github.com/unitreerobotics/xr_teleoperate/blob/main/.gitmodules)。

## BrainCo Revo2

XR側の `r` は追従開始です。腕の指令を入れるとRevo2のmimic拘束が発散していた問題に対し、手の関節に数値安定化用の追加慣性を設定しました。腕・指の同時指令とリセットを含む自動再現試験で発散しないことを確認しています。**公式の物性値だけのモデルではありません**（追加慣性の説明は下記）。既存G1の脚には関節範囲を超える振動が残るため、この試験をロボット全体の安定性確認とは扱いません。Questでの操作・把持・XR記録も未確認です。

`docker/` 内からシミュレータを起動します。

```bash
docker compose run --rm sim sim-brainco
```

別のデスクトップ端末でリポジトリルートから操作・記録を起動します。

```bash
./docker/teleop.sh --ee brainco
# ハンドトラッキングの場合
./docker/teleop.sh --ee brainco --input-mode hand
```

タスク名は `Isaac-PickPlace-Cylinder-G129-Brainco-Joint`、DDSフラグは `--enable_brainco_dds` です。共通の `G1RobotPresets.g1_29dof_brainco_base_fix()` とBrainCo DDS・状態取得処理は別シーンからも再利用できます。今回はベース固定の円柱シーンを対象とし、歩行・再生・触覚は対応しません。

G1本体・腕・手首とカメラは既存Dex3モデルを参照し、手だけを差し替えます。公式モデルはビルド時に取得します。初回起動時に派生USDを既存の `isaac-cache` 内へ生成するため、手動のアセット配置は不要です。コードのbind mountはassets・teleimagerを隠しません。

仕様の基準は次の固定版です。

- DDS: [Unitree brainco_hand_service / d71996b6](https://github.com/unitreerobotics/brainco_hand_service/tree/d71996b6999edb2f838a3dca3d9621429a2ef966)
- 手のUSD・URDF・mimic・リンク慣性: [BrainCo brainco-description / f332a6f0](https://github.com/BrainCoTech/brainco-description/tree/f332a6f0dc944e26b82976b637074b03f7ee8a2c/revo2_system)
- 手首への取り付けとアダプタ: [Unitree unitree_ros / 7d6075f7](https://github.com/unitreerobotics/unitree_ros/tree/7d6075f7f58588b189b940130e3edab3c839b2df/robots/g1_with_brainco_hand)

DDSは左右それぞれ `rt/brainco/{left,right}/{cmd,state}`、型は `MotorCmds_` / `MotorStates_`、各6軸です。順序は **Thumb Flex (proximal)、Thumb Aux (metacarpal)、Index、Middle、Ring、Pinky**。シミュレーションは既存のdomain 1、公式実機サービスはdomain 0です。

位置指令は公式サービスと同じfloat32のclamp・1000倍・整数化を行い、URDFの関節範囲へ線形変換します。状態は実際の関節位置から求め、起動直後から指令なしでも100 Hzを目標に送信します。速度指令はURDF速度上限に対する目標角の変化率として近似し、0では目標を保持します。速度stateもURDF速度上限で正規化した近似です。実機内部の速度制御と同一ではありません。`tau_est` は公式では電流由来のため、関節トルクを入れず未再現値の0を返します。

手のゲイン `stiffness=100、damping=1` は公式USD相当の検証開始値で、実機の公式ゲインではありません。接触・把持時の安定性は利用環境で確認してください。mimicは公式URDFの関係をPhysX拘束として設定します。

公式URDFで空の指先リンクは、質量のない座標フレームとして先端リンク下へ配置します。USDの `mass=0` を持つ剛体として残すとPhysXが質量を自動補完するためです。各関節に公式の位置・速度上限を設定し、連動先の速度上限も超えないよう駆動側の速度を制限します。例えば人差し指は `2.2685 / 1.155 ≈ 1.9641 rad/s` が駆動側の上限です。

Revo2の左右各11関節（6駆動＋5連動）に `physxJoint:armature=0.01 kg·m²` を設定します。[PhysXの追加慣性](https://docs.omniverse.nvidia.com/kit/docs/omni_physics/latest/dev_guide/guides/articulation_stability_guide.html#joint-armature)による数値安定化で、本タスクのCPU・物理刻み5 msで検証した調整値です。**BrainCo公式値や実機モータの推定慣性ではありません。** リンクの質量・慣性テンソルは公式値を維持しますが、関節空間の有効慣性は増えるため、公式慣性のみを使う当初計画からの変更です。対象は位置操作・記録であり、実機との動力学・接触力の一致は未検証です。連動関節には独立した位置駆動を追加せず、mimic比率・offsetも変更しません。G1本体・腕の設定と物理周期は維持します。

画像・腕・左右各6軸のハンド指令／状態は既存の記録処理を使い、保存先・所有者・形式を維持します。XR側のBrainCoの親指順序・正規化・コントローラ割り当ては取り込み時の実装を使用します。一時的に加えた親指2軸の入れ替えは取り消しました。Sim側は実機DDSと同じモータ順序を維持し、XR側の並びに合わせた追加の入れ替えは行いません。このため、元のXRの親指割り当ても実機・Simの両方に同じように適用されます。入れ替え修正中に収集したBrainCoデータとは親指2軸の指令の意味が異なります。過去データは自動変換しません。実機との応答速度・接触挙動の一致は未検証です。

自動DDS検査は、実機や稼働中のシミュレータと接続しない隔離ネットワークのコンテナで `unitree_sim_env` を有効にし、シミュレータディレクトリから次を実行します。

```bash
python -m unittest discover -s tests -p test_brainco.py -v
python tests/check_brainco_sim.py
# カメラを有効にして確認用画像も保存する場合
python tests/check_brainco_sim.py --images /tmp/brainco-frames
```

自動物理試験は24秒分の追従開始相当の腕指令、左右の全開・半開・全閉、腕と各指の連続同時指令、`env.reset()`を実行します。非有限値、手の位置・速度上限違反、mimic誤差、実測位置と返送用stateの不一致を失敗として扱い、例外時は終了コード1を返します。修正前イメージでは追従開始直後に失敗し、修正後イメージ単独とカメラ有効時の両方で通過しました。mimic誤差は最大約0.00030 rad、stateの位置誤差は0でした。正面・左右手首・俯瞰カメラの画像取得も確認しました。

脚の関節範囲違反は別に出力し、全体の安定性を確認済みと誤表示しません。既存Dex3・Inspireは10秒分の腕指令で計算を継続しましたが、同じCPU・物理周期の条件でDex3の右足首、Inspireの右膝にも範囲違反を確認しています。この本体側の問題は未修正です。

以前の検証は、ビルド・DDSテスト4件・構造検査と、腕の追従指令を入れない手単独の位置操作・画像取得に限られていました。既存Dex3・Inspireについても起動と短時間のステップ実行、本体DDS順序を確認した範囲です。これらをテレオペレーション全体の動作確認済みと扱ったことは誤りでした。

未実施: Questのコントローラ／ハンドトラッキングを通した操作、円柱の把持・持ち上げ・接触時の安定性、XRによる記録ファイルの収集。これらは利用環境での確認対象です。手のゲインは上記の初期値を維持しており、把持に合わせた調整はしていません。
