def generate_filename(radius, chord_length, drawing_type):
    """生成文件名（返回安全的单个文件名，不包含路径分隔符）。"""
    # 使用英文全角“／“替代可能的路径分隔符，保证在 join 时不会创建额外目录
    safe_type = str(drawing_type).replace('/', '／').replace('\\', '／')
    if radius < 0:
        return f"{safe_type}／-R{abs(radius):.3f}-Φ {chord_length:.3f}"
    else:
        return f"{safe_type}／R{radius:.3f}-Φ {chord_length:.3f}"
