# XR Teleoperate

`docker compose` は `docker/` 内、`./docker/…` はリポジトリルートで実行します。

## ビルド

```bash
cd docker
docker compose build      # 両方
# 必要な方だけ
docker compose build xr   # テレオペ
docker compose build sim  # シミュレーション
```

## シミュレーションとXRの起動
0. 初回は`cp docker/.env.sim.example docker/.env.sim` で設定ファイルを作成
1. `docker/.env` の`IMG_SERVER_IP` をQuestから接続できる画像サーバーPCのLAN IPに`NETWORK_INTERFACE` をテレオペを動かすPCのネットワークインターフェース名に設定。
2. シミュレーションの起動
```bash
./docker/sim.sh
```
3. テレオペの起動
```bash
./docker/teleop-sim.sh
```

Questで `https://<XRを動かすPCのIP>:8012/` を開き、証明書の警告が出た場合は承認してください。

テレオペを起動した端末で、`r`：追従開始、`s`：記録開始／保存、`t`：物体のみリセット（シミュレーション限定）、`q`：終了。

`t` は追従開始前にも使え、記録の開始・保存は行いません。記録中なら記録を継続します。

## 実機での起動
0. 初回は`cp docker/.env.real.example docker/.env.real` で設定ファイルを作成
1. `docker/.env` の `IMG_SERVER_IP` を画像サーバーPCのIP、`NETWORK_INTERFACE` をテレオペを動かすPCのネットワークインターフェース名に設定。
2. コントローラのL2＋R2を長押しして、G1をDeveloperモードにする
3. テレオペ起動

```bash
./docker/teleop-real.sh
```

## 3指、5指の切り替え
コマンドの末尾に以下を付ける。
```bash
# 3指ハンド
./docker/teleop-real.sh　--ee dex3
# 5指ハンド
./docker/teleop-real.sh　--ee brainco
```
何も指定しなかったら3指ハンドになる。
## コントローラ、ハンドトラッキングの切り替え
コマンドの末尾に以下を付ける

```bash
# ハンドトラッキング
./docker/teleop-real.sh　--input-mode hand
# コントローラ
./docker/teleop-real.sh　--input-mode controller
```
何も指定しなかったらコントローラになる。
## タスクの変更

Sim起動時に `--task` を追加します。

```bash
# 赤いブロック（Dex3）
./docker/sim.sh --task Isaac-PickPlace-RedBlock-G129-Dex3-Joint

# 赤いブロックを引き出しに入れる（Dex3）
./docker/sim.sh --task Isaac-Pick-Redblock-Into-Drawer-G129-Dex3-Joint
```

XR側の起動コマンドは同じです。Revo2は現在、円柱タスクのみ対応しています。

## データセット名、言語指示の変更

データセット名は`--task-name` を、言語指示は'--task-goal'を指定します。

```bash
./docker/teleop-sim.sh --task-name red_block_01　--task-goal "pick up the red block"
```

ホストの `data/<指定した名前>/episode_XXXX/` に保存します。同じ名前で再起動するとエピソードを追加します。

## PCに複数のカメラを接続してサーバーを立てるときのの設定
docker/cam_config_server.yamlを編集する。以下は左手カメラの設定の例。realsenseを想定。
```
# =====================================================
# Left wrist camera configuration
# =====================================================
left_wrist_camera:
  enable_zmq: true
  zmq_port : 55556
  enable_webrtc: true
  webrtc_port : 60002
  webrtc_codec: h264
  type: realsense
  image_shape: [480, 640]
  binocular: false
  fps: 30
  video_id: null
  serial_number: "218622278518"
  physical_path: null
```
- 使わないカメラのenable_zmqとenable_webrtcはfalseにする
- binocularはfalseにする。
- realsenseのシリアルナンバーをserial_numberに設定する。

以下を実行してカメラサーバーを起動する。
```
cd docker

devices=()
for dev in /dev/video*; do
  [[ -c "$dev" ]] && devices+=(-v "$dev:$dev")
done

docker compose run --rm \
  -v /dev/bus/usb:/dev/bus/usb \
  "${devices[@]}" \
  image-server image-server --rs
```

## ロボット視点でテレオペ
一度メタクエスト上でブラウザから
