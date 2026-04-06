import { defineStore } from 'pinia'
import axios from 'axios'

const api = axios.create({
  baseURL: '',
  timeout: 10000
})

export const useAudioStore = defineStore('audio', {
  state: () => ({
    enabled: false,
    musicEnabled: false,
    soundVolume: 0.7,
    musicVolume: 0.5,
    soundFiles: {
      coins: '',
      button: '',
      task: '',
      equip: '',
      attack: '',
      levelup: '',
      cultivate: '',
    },
    musicBgm: '',
    audioContext: null,
    loadedSounds: {},
    currentMusic: null,
    isInitialized: false,
  }),

  actions: {
    async init() {
      if (this.isInitialized) return
      
      try {
        const resp = await fetch('/api/audio/config')
        const data = await resp.json()
        if (data.success && data.data) {
          this.enabled = data.data.enabled
          this.musicEnabled = data.data.music_enabled
          this.soundVolume = data.data.sound_volume
          this.musicVolume = data.data.music_volume
          this.soundFiles.coins = data.data.sound_coins
          this.soundFiles.button = data.data.sound_button
          this.soundFiles.task = data.data.sound_task
          this.soundFiles.equip = data.data.sound_equip
          this.soundFiles.attack = data.data.sound_attack
          this.soundFiles.levelup = data.data.sound_levelup || ''
          this.soundFiles.cultivate = data.data.sound_cultivate || ''
          this.musicBgm = data.data.music_bgm
        }
      } catch (e) {
        console.error('加载音效配置失败', e)
      }
      
      if (typeof window !== 'undefined' && !this.audioContext) {
        try {
          this.audioContext = new (window.AudioContext || window.webkitAudioContext)()
        } catch (e) {
          console.warn('Web Audio API 不支持')
        }
      }
      
      this.isInitialized = true
    },

    async updateSettings(settings) {
      try {
        const resp = await fetch('/api/audio/settings', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(settings)
        })
        const data = await resp.json()
        if (data.success) {
          if (settings.enabled !== undefined) this.enabled = settings.enabled
          if (settings.music_enabled !== undefined) this.musicEnabled = settings.music_enabled
          if (settings.sound_volume !== undefined) this.soundVolume = settings.sound_volume
          if (settings.music_volume !== undefined) this.musicVolume = settings.music_volume
        }
        return data
      } catch (e) {
        console.error('保存音效设置失败', e)
        return { success: false }
      }
    },

    async playSound(type) {
      if (!this.enabled || !this.audioContext) return
      
      const soundFile = this.soundFiles[type]
      if (!soundFile) return

      try {
        if (this.audioContext.state === 'suspended') {
          await this.audioContext.resume()
        }

        const response = await fetch(soundFile)
        const arrayBuffer = await response.arrayBuffer()
        const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer)
        
        const source = this.audioContext.createBufferSource()
        const gainNode = this.audioContext.createGain()
        
        gainNode.gain.value = this.soundVolume
        source.buffer = audioBuffer
        source.connect(gainNode)
        gainNode.connect(this.audioContext.destination)
        
        source.start(0)
      } catch (e) {
        console.warn(`播放音效失败: ${type}`, e)
      }
    },

    async playMusic() {
      if (!this.musicEnabled || !this.musicBgm || !this.audioContext) return
      
      try {
        if (this.audioContext.state === 'suspended') {
          await this.audioContext.resume()
        }

        if (this.currentMusic) {
          this.currentMusic.pause()
        }

        this.currentMusic = new Audio(this.musicBgm)
        this.currentMusic.loop = true
        this.currentMusic.volume = this.musicVolume
        await this.currentMusic.play()
      } catch (e) {
        console.warn('播放背景音乐失败', e)
      }
    },

    stopMusic() {
      if (this.currentMusic) {
        this.currentMusic.pause()
        this.currentMusic = null
      }
    },

    setSoundVolume(volume) {
      this.soundVolume = Math.max(0, Math.min(1, volume))
      this.updateSettings({ sound_volume: this.soundVolume })
    },

    setMusicVolume(volume) {
      this.musicVolume = Math.max(0, Math.min(1, volume))
      this.updateSettings({ music_volume: this.musicVolume })
      if (this.currentMusic) {
        this.currentMusic.volume = this.musicVolume
      }
    },

    toggleSound(enabled) {
      this.enabled = enabled
      this.updateSettings({ enabled })
    },

    toggleMusic(enabled) {
      this.musicEnabled = enabled
      this.updateSettings({ music_enabled: enabled })
      if (enabled) {
        this.playMusic()
      } else {
        this.stopMusic()
      }
    },
  },
})

export default useAudioStore
