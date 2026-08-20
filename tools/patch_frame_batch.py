import pathlib

ai_path = pathlib.Path(r"D:\code\video-note\src\services\ai_service.py")
t = ai_path.read_text(encoding="utf-8")

# Replace the frame analysis logic to batch frames
old_analyze = '''    @with_retry(max_retries=3, base_delay=3.0)
    async def analyze_frames(self, frame_paths: List[str], prompt: str) -> str:
        if not frame_paths:
            return ""
        logger.info("Analyzing %d frames via VLM", len(frame_paths))
        max_frames = 10
        if len(frame_paths) > max_frames:
            step = max(1, len(frame_paths) // max_frames)
            frame_paths = frame_paths[::step][:max_frames]
        content = [{"type": "text", "text": prompt}]
        for path in frame_paths:
            p = Path(path)
            if not p.exists():
                continue
            b64 = base64.b64encode(p.read_bytes()).decode()
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
        response = await self._vlm.chat.completions.create(
            model=self.vlm_model, messages=[{"role": "user", "content": content}], max_tokens=4096)
        return response.choices[0].message.content or ""'''

new_analyze = '''    @with_retry(max_retries=3, base_delay=3.0)
    async def analyze_frames(self, frame_paths: List[str], prompt: str) -> str:
        if not frame_paths:
            return ""
        
        # Sample frames if too many (max 20 for better coverage)
        max_frames = 20
        if len(frame_paths) > max_frames:
            step = max(1, len(frame_paths) // max_frames)
            frame_paths = frame_paths[::step][:max_frames]
        
        logger.info("Analyzing %d frames via VLM (batched)", len(frame_paths))
        
        # Batch frames: 5 per batch to avoid API limits
        batch_size = 5
        all_analyses = []
        
        for i in range(0, len(frame_paths), batch_size):
            batch = frame_paths[i:i + batch_size]
            content = [{"type": "text", "text": f"{prompt}\n\nFrame batch {i//batch_size + 1}/{(len(frame_paths) + batch_size - 1)//batch_size}:"}]
            
            for path in batch:
                p = Path(path)
                if not p.exists():
                    continue
                # Use streaming read for large files
                b64 = base64.b64encode(p.read_bytes()).decode()
                content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
            
            try:
                response = await self._vlm.chat.completions.create(
                    model=self.vlm_model, messages=[{"role": "user", "content": content}], max_tokens=2048)
                analysis = response.choices[0].message.content or ""
                if analysis:
                    all_analyses.append(analysis)
                    logger.info("Frame batch %d/%d analyzed", i//batch_size + 1, (len(frame_paths) + batch_size - 1)//batch_size)
            except Exception as e:
                logger.warning("Frame batch %d failed: %s", i//batch_size + 1, e)
                continue
        
        return "\\n\\n".join(all_analyses) if all_analyses else ""'''

t = t.replace(old_analyze, new_analyze, 1)

ai_path.write_text(t, encoding="utf-8")
print("ai_service.py frame batching patched")
