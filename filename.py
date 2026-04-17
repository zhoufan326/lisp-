def generate_filename(radius, chord_length, drawing_type):
    """生成文件名（返回安全的单个文件名，不包含路径分隔符）。"""
    # 确保参数类型正确
    try:
        radius = float(radius)
        chord_length = float(chord_length)
        drawing_type = str(drawing_type)
    except (ValueError, TypeError):
        # 如果参数转换失败，返回默认文件名
        return "DRAWING"
    
    # 使用英文全角"／"替代可能的路径分隔符，保证在 join 时不会创建额外目录
    safe_type = drawing_type.replace('/', '／').replace('\\', '／')
    
    if radius < 0:
        return f"{safe_type}／-R{abs(radius):.3f}-Φ {chord_length:.3f}"
    else:
        if drawing_type == "JZM":
            return f"{safe_type}／±R{radius:.3f}-Φ {chord_length:.3f}"
        else:
            return f"{safe_type}／R{radius:.3f}-Φ {chord_length:.3f}"