def get_session_from_path(path):
    # strip "/socket/" from the start
    session = path[8:]
    # Ensure that the session is six digits
    if len(session)!= 6:
        return None
    try:
        int(session)
    except ValueError:
        return None

    return session


def print_segments(segments):
    return "\n".join(
        [" ".join(["          ", str(x["start"]), str(x["end"]), str(x["text"])]) for x in segments]
    )


def cleanup_files(session):
    if os.path.exists(session + streamed_audio):
        os.remove(session + streamed_audio)
    if os.path.exists(session + decompressed_wave):
        os.remove(session + decompressed_wave)
