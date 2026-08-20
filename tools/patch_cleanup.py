import pathlib

# Patch engine.py to add cleanup after processing
engine_path = pathlib.Path(r"D:\code\video-note\src\core\engine.py")
t = engine_path.read_text(encoding="utf-8")

# Add cleanup method to VideoNoteEngine
old_init = '''    def retry_task(self, task_id: str):'''
new_cleanup = '''    def _cleanup_temp_files(self, video_path: str) -> None:
        """Clean up temp audio and frame files after processing."""
        import shutil
        video_name = Path(video_path).stem
        
        # Clean audio temp file
        audio_path = Path("./data/temp") / f"{video_name}.m4a"
        old_audio = Path("./data/temp") / f"{video_name}.mp3"
        for p in (audio_path, old_audio):
            try:
                if p.exists():
                    p.unlink()
                    logger.info("Cleaned temp audio: %s", p)
            except OSError as e:
                logger.warning("Failed to clean %s: %s", p, e)
        
        # Clean frame directory
        frames_dir = Path("./data/temp/frames") / video_name
        try:
            if frames_dir.exists():
                shutil.rmtree(frames_dir)
                logger.info("Cleaned temp frames: %s", frames_dir)
        except OSError as e:
            logger.warning("Failed to clean %s: %s", frames_dir, e)

    def retry_task(self, task_id: str):'''
t = t.replace(old_init, new_cleanup, 1)

# Call cleanup after successful processing
old_complete = '''        note_path = data.get("note_path", "")
        self.checkpoint.save_progress(task_id, ProcessingStage.COMPLETED, 1.0, data)'''
new_complete = '''        note_path = data.get("note_path", "")
        self.checkpoint.save_progress(task_id, ProcessingStage.COMPLETED, 1.0, data)
        self._cleanup_temp_files(video_path)'''
t = t.replace(old_complete, new_complete, 1)

engine_path.write_text(t, encoding="utf-8")
print("engine.py patched")
