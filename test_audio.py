import sounddevice as sd
import sys

print("="*60)
print("🎤 TEST DIAGNOSTIC AUDIO")
print("="*60)

try:
    print(f"Python: {sys.version}")
    print(f"SoundDevice version: {sd.__version__}")
    
    print("\n📋 Périphériques Audio Détectés:")
    devices = sd.query_devices()
    print(devices)
    
    default_in = sd.default.device[0]
    print(f"\n✅ Périphérique d'entrée par défaut: ID {default_in}")
    
    device_info = sd.query_devices(default_in, 'input')
    print(f"   Nom: {device_info['name']}")
    print(f"   Channels: {device_info['max_input_channels']}")
    print(f"   Sample Rate par défaut: {device_info['default_samplerate']}")
    
    print("\n🔊 Test d'ouverture du flux (0.5 sec)...")
    # Test simple stream
    with sd.InputStream(device=default_in, channels=1, samplerate=24000) as stream:
        print("   ✅ Flux ouvert avec succès (Microphone actif)")
        sd.sleep(500)
        print("   ✅ Flux refermé")

except Exception as e:
    print(f"\n❌ ERREUR AUDIO: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)

