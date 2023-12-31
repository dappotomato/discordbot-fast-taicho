import gc
import asyncio

import librosa
import numpy as np
import wave
from pydub.audio_segment import AudioSegment
import youtube_dl


class Wav_Karaoke:
    def __init__(self,user_id:int) -> None:
        """
        カラオケのクラス

        self.filename               :str
            ダウンロードする音楽ファイルの相対パス
        self.music_file_path        :str
            ダウンロードした音楽ファイルの相対パス
        self.voice_file_path        :str
            録音音声ファイルの相対パス
        self.ratio_music_file_path  :str
            60秒に収めた音楽ファイルの相対パス
        self.ratio_voice_file_path  :str
            60秒に収めた録音音声ファイルの相対パス
        """
        self.filename = f".\wave\{user_id}_music"
        self.music_file_path = f'.\wave\{user_id}_music.wav'
        self.voice_file_path = f'.\wave\{user_id}_voice.wav'
        self.ratio_music_file_path = f'.\wave\{user_id}_ratio_music.wav'
        self.ratio_voice_file_path = f'.\wave\{user_id}_ratio_voice.wav'
        self.loop = asyncio.get_event_loop()

    async def music_wav_open(self) -> AudioSegment:   #音楽のwavファイルを開く
        base_sound = AudioSegment.from_file(self.music_file_path, format="wav")
        return base_sound

    async def music_wav_second(self) -> float:   #音楽のwavファイルの秒数を返す
        base_sound:AudioSegment = AudioSegment.from_file(self.music_file_path, format="wav")
        return base_sound.duration_seconds

    async def voice_wav_open(self) -> AudioSegment:   #録音音声のwavファイルを開く
        base_sound = AudioSegment.from_file(self.voice_file_path, format="wav")
        return base_sound

    async def voice_wav_second(self) -> float:   #録音音声のwavファイルの秒数を返す
        base_sound:AudioSegment = AudioSegment.from_file(self.voice_file_path, format="wav")
        return base_sound.duration_seconds

    # サンプリング周波数を計算
    async def get_sampling_frequency(self,file_path:str) -> int:
        wr = wave.open(file_path, "r")
        fs = wr.getframerate()
        wr.close()
        return fs

    async def limit_wav_duration(self):   #wavファイルの秒数を60秒以内に収める
        """
        wavファイルを60秒に収める理由
        採点で使用するDTW(動的タイムワープ方式)は2種類の時系列データの比較を行うもの。
        長さが異なるものも比較できるが、異なる分だけ対応付けをしなければならないので、メモリにデータを残さないといけない。
        約1GBを許容範囲とした結果、wavファイルを60秒に抑えることにした。
        """
        # 基となる音声ファイルの相対パス
        before_values = [
            self.music_file_path,
            self.voice_file_path
        ]

        # 60秒に収めた音楽ファイルの相対パス
        after_values = [
            self.ratio_music_file_path,
            self.ratio_voice_file_path
        ]
        for before_value,after_value in zip(before_values,after_values):
            before_sound:AudioSegment = AudioSegment.from_file(before_value, format="wav")
            time = before_sound.duration_seconds

            # 60秒以上の場合
            if time >= 60:
                speed = time/60
                base_sound = before_sound.speedup(playback_speed=speed, crossfade=0)
            # 60秒未満の場合、そのまま
            else :
                base_sound = before_sound
            # 書き込み
            base_sound.export(after_value, format="wav")

    # 採点(類似度計算)
    async def calculate_wav_similarity(self):

        path_list = [
            self.ratio_music_file_path,
            self.ratio_voice_file_path
        ]
    
        # 各wavファイルの振幅データ列とサンプリング周波数を取得し、リストに格納
        x_and_fs_list = []
        for path in path_list:
            x, fs = await self.loop.run_in_executor(
                executor=None,
                func=librosa.load(
                    path,
                    await self.get_sampling_frequency(path)
                )
            )
            x_and_fs_list.append((x, fs))
            
        # 使用する特徴量を抽出し、リストに格納
        feature_list = []
        for x_and_fs in x_and_fs_list:
            feature = await self.loop.run_in_executor(
                executor=None,
                func=librosa.feature.spectral_centroid(
                    x_and_fs[0], 
                    x_and_fs[1]
                )
            )
            feature_list.append(feature)

        # メモリ削減のため、特徴量を削除
        del x_and_fs_list
        del path_list
        gc.collect()

        # 類似度を計算
        ac, wp = await self.loop.run_in_executor(
            executor=None,
            func=librosa.sequence.dtw(
                feature_list[0], 
                feature_list[1]
            )
        )
        # -1で一番最後の要素を取得
        eval = 1 - (ac[-1][-1] / np.array(ac).max())

        return round(eval*100,4)

    # youtube-dlでダウンロード
    async def song_dl(self,video_url:str) -> None:
        filename = self.filename
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl':  filename + '.%(ext)s',
            'postprocessors': [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'wav',
                    'preferredquality': '192'
                },
                {
                    'key': 'FFmpegMetadata'
                },
            ],
        }
        ydl = youtube_dl.YoutubeDL(ydl_opts)
        await self.loop.run_in_executor(
            None, 
            lambda: ydl.extract_info(
                video_url, 
                download=True
            )
        )
