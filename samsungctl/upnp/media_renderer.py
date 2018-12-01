# -*- coding: utf-8 -*-

from samsungctl.upnp import UPNPControlBase


class MediaRenderer(UPNPControlBase):

    def __init__(self, url, location):
        self.rendering_control = None
        self.connection_manager = None
        self.av_transport = None
        UPNPControlBase.__init__(self, url, location)

    def __str__(self):
        output = 'MediaRenderer\n' + '=' * 40 + '\ninstance.media_renderer.rendering_control\n'
        output += str(self.rendering_control)
        output += '\ninstance.media_renderer.connection_manager\n'
        output += str(self.connection_manager)
        output += '\ninstance.media_renderer.av_transport\n'
        output += str(self.av_transport)
        return output

    @property
    def media_info(self):
        (
            track_count,
            media_duration,
            media_uri,
            media_metadata,
            next_uri,
            next_metadata,
            playback_device,
            record_device,
            write_status
        ) = self.av_transport.GetMediaInfo(0)

        return dict(
            track_count=track_count,
            media_duration=media_duration,
            media_uri=media_uri,
            media_metadata=media_metadata,
            next_uri=next_uri,
            next_metadata=next_metadata,
            playback_device=playback_device,
            record_device=record_device,
            write_status=write_status
        )

    @property
    def transport_info(self):
        state, status, speed =  self.av_transport.GetTransportInfo(0)
        return dict(
            state=state,
            status=status,
            speed=speed
        )

    @property
    def device_capabilities(self):
        play_media, record_media, record_quality = (
            self.av_transport.GetDeviceCapabilities(0)
        )

        return dict(
            play_media=play_media,
            record_media=record_media,
            record_quality=record_quality
        )

    def set_av_transport_uri(self, uri, metadata):
        self.av_transport.SetAVTransportURI(
            0,
            uri,
            metadata
        )  # metadata escaped xm

    @property
    def transport_settings(self):
        play_mode, record_quality = self.av_transport.GetTransportSettings(0)
        return dict(play_mode=play_mode, record_quality=record_quality)

    def seek(self, seek_mode, amount):
        self.av_transport.Seek(0, seek_mode, amount)

    @property
    def position_info(self):
        (
            track_number,
            track_duration,
            track_metadata,
            track_uri,
            relative_time,
            absolute_time,
            relative_count,
            absolute_count
        ) = self.av_transport.GetPositionInfo(0)

        return dict(
            track_number=track_number,
            track_duration=track_duration,
            track_metadata=track_metadata,
            track_uri=track_uri,
            relative_time=relative_time,
            absolute_time=absolute_time,
            relative_count=relative_count,
            absolute_count=absolute_count
        )

    @property
    def transport_actions(self):
        return self.av_transport.GetCurrentTransportActions(0)[0]

    def get_connection_info(self, connection_id):
        (
            rcs_id,
            av_transport_id,
            protocol_info,
            peer_connection_manager,
            peer_connection_id,
            direction,
            status
        ) = self.connection_manager.GetCurrentConnectionInfo(connection_id)

        return dict(
            rcs_id=rcs_id,
            av_transport_id=av_transport_id,
            protocol_info=protocol_info,
            peer_connection_manager=peer_connection_manager,
            peer_connection_id=peer_connection_id,
            direction=direction,
            status=status
        )

    @property
    def protocol_info(self):
        source, sink = self.connection_manager.GetProtocolInfo()
        sink = list(itm.strip() for itm in sink.split(','))

        return dict(source=source, sink=sink)

    @property
    def connection_ids(self):
        return self.connection_manager.GetCurrentConnectionIDs()[0]

    def prepare_for_connection(
        self,
        remote_protocol_info,
        peer_connection_manager,
        peer_connection_id,
        direction
    ):
        connection_id, av_transport_id, rcs_id = (
            self.connection_manager.PrepareForConnection(
                remote_protocol_info,
                peer_connection_manager,
                peer_connection_id,
                direction
            )
        )

        return dict(
            connection_id=connection_id,
            av_transport_id=av_transport_id,
            rcs_id=rcs_id
        )

    def connection_complete(self, connection_id):
        self.connection_manager.ConnectionComplete(connection_id)

    @property
    def presets(self):
        return self.rendering_control.ListPresets(0)[0]

    def select_preset(self, preset_name):
        self.rendering_control.SelectPreset(0, preset_name)

    def get_channel_mute(self, channel):
        return self.rendering_control.GetMute(0, channel)[0]

    def set_channel_mute(self, channel, desired_mute):
        self.rendering_control.SetMute(0, channel, desired_mute)

    def get_channel_volume(self, channel):
        return self.rendering_control.GetVolume(0, channel)[0]

    def set_channel_volume(self, channel, desired_volume):
        self.rendering_control.SetVolume(0, channel, desired_volume)

    @property
    def brightness(self):
        return self.rendering_control.GetBrightness(0)[0]

    @brightness.setter
    def brightness(self, desired_brightness):
        self.rendering_control.SetBrightness(0, desired_brightness)

    @property
    def contrast(self):
        return self.rendering_control.GetContrast(0)[0]

    @contrast.setter
    def contrast(self, desired_contrast):
        self.rendering_control.SetContrast(0, desired_contrast)

    @property
    def sharpness(self):
        return self.rendering_control.GetSharpness(0)[0]

    @sharpness.setter
    def sharpness(self, desired_sharpness):
        self.rendering_control.SetSharpness(0, desired_sharpness)

    @property
    def color_temperature(self):
        return self.rendering_control.GetColorTemperature(0)[0]

    @color_temperature.setter
    def color_temperature(self, desired_color_temperature):
        self.rendering_control.SetColorTemperature(
            0,
            desired_color_temperature
        )

    @property
    def x_dlna_get_byte_position_info(self):
        track_size, relative_bytes, absolute_bytes = (
            self.av_transport.X_DLNA_GetBytePositionInfo(0)
        )

        return dict(
            track_size=track_size,
            relative_bytes=relative_bytes,
            absolute_bytes=absolute_bytes
        )

    @property
    def x_audio_selection(self):
        audio_pid, audio_encoding = (
            self.rendering_control.X_GetAudioSelection(0)
        )
        return dict(audio_pid=audio_pid, audio_encoding=audio_encoding)

    @x_audio_selection.setter
    def x_audio_selection(self, value):
        """value = (audio_pid, audio_encoding)"""
        audio_pid, audio_encoding = value
        self.rendering_control.X_UpdateAudioSelection(
            0,
            audio_pid,
            audio_encoding
        )

    @property
    def x_video_selection(self):
        video_pid, video_encoding = (
            self.rendering_control.X_GetVideoSelection(0)
        )

        return dict(video_pid=video_pid, video_encoding=video_encoding)

    @x_video_selection.setter
    def x_video_selection(self, value):
        """value = video_pid, video_encoding"""
        video_pid, video_encoding = value
        self.rendering_control.X_UpdateVideoSelection(
            0,
            video_pid,
            video_encoding
        )


