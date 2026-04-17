(defun xba (r0 a0 t0 b0 tool_type tech_choice custom_tech_text /
               old_osmode old_cmdecho old_orthomode old_clayer old_attdia old_dimtofl product_name material drawing_prefix r3_circle_ent)
  ;;===============定义程序名称和参数：使用defun函数定义程序，并声明局部变量===============
  (vl-load-com)  ; 加载ActiveX支持
  ;; 保存原始系统变量
  (setq old_osmode (getvar "osmode"))
  (setq old_cmdecho (getvar "cmdecho"))
  (setq old_orthomode (getvar "orthomode"))
  (setq old_clayer (getvar "clayer"))
  (setq old_attdia (getvar "attdia"))
  (setq old_dimtofl (getvar "dimtofl"))
  
  ;; 设置错误处理函数
  (defun *error* (msg)
    (if (/= msg "Function cancelled")
      (progn
        (princ "\n")
        (princ "出错了: ")
        (princ msg)
      )
    )
    ;; 恢复原始系统变量
    (setvar "osmode" old_osmode)
    (setvar "cmdecho" old_cmdecho)
    (setvar "orthomode" old_orthomode)
    (setvar "clayer" old_clayer)
    (setvar "attdia" old_attdia)
    (setvar "dimtofl" old_dimtofl)
    ;; 退出函数
    (princ)
  )
  
  ;; 设置新的系统变量
  (setvar "osmode" 0)       ;对象捕捉
  (setvar "cmdecho" 0)      ;回显提示和输入
  (setvar "orthomode" 0)    ;正交模式
  (setvar "attdia" 0)       ;关闭属性对话框，以便程序控制
  
  
  ;;=================工装类型选择===================
  (princ "\n=== 下摆凹工装绘图程序 ===")
  
  (if (null tool_type)
    (progn
      (initget 1 "1 2")
      (setq tool_type (getkword "\n请选择工装类型: 1. 抛光模基模 2. 精磨模基模 "))
    )
  )
  
  ;; 根据工装类型设置参数
  (cond
    ((= tool_type "1")
     (setq product_name "抛光模基模")
     (setq material "H59-1")
     (setq drawing_prefix "XPMJM"))
    
    ((= tool_type "2")
     (setq product_name "精磨模基模")
     (setq material "H59-1")
     (setq drawing_prefix "XJMJM"))

    (T
     (princ "\n选择无效，程序终止。")
     (exit))
  )
  ;;验证获取的工装名称，材料，图号前缀
  (princ (strcat "\n=== " product_name " ==="))
  (princ (strcat "\n材料: " material))
  (princ (strcat "\n图号前缀: " drawing_prefix))
  
  ;;=================获取用户输入：使用函数获取用户输入的参数=========================
  (princ "\n=== 下摆凹工装绘图程序 ===")
  (if (null r0) (setq r0 (getdist "\n请输入曲率半径: ")))
  (if (null a0) (setq a0 (getdist "\n请输入口径(直径): ")))
  (if (null t0) (setq t0 (getdist "\n请输入平台宽度: ")))
  (if (null b0) (setq b0 (getdist "\n请输入柄长: ")))
  
  ;; 验证输入参数的合理性
  (if (or (null r0) (null a0) (null t0) (null b0) (<= r0 0) (<= a0 0) (<= t0 0) (<= b0 0))
    (progn
      (princ "\n错误: 参数值必须大于0且不能为空。")
      ;; 恢复原始系统变量
      (setvar "osmode" old_osmode)
      (setvar "cmdecho" old_cmdecho)
      (setvar "orthomode" old_orthomode)
      (setvar "clayer" old_clayer)
      (setvar "attdia" old_attdia)
      (princ)
      (exit)
    )
  )
  
  ;; 检查曲率半径是否足够大以容纳口径
  (if (< (* 2 r0) a0)
    (progn
      (princ "\n曲率半径过小，无法容纳指定口径，程序终止。")
      ;; 恢复原始系统变量
      (setvar "osmode" old_osmode)
      (setvar "cmdecho" old_cmdecho)
      (setvar "orthomode" old_orthomode)
      (setvar "clayer" old_clayer)
      (setvar "attdia" old_attdia)
      (princ)
      (exit)
    )
  )
  
  ;; 询问技术要求选择
  (if (null tech_choice)
    (progn
      (princ "\n=== 技术要求选择 ===")
      (princ "\n请选择1: 使用默认技术要求;2: 自定义技术要求:")
      (setq tech_choice (getint))
    )
  )
  (if (or (null tech_choice) (< tech_choice 1) (> tech_choice 2)) (setq tech_choice 1))
  
  (if (and (= tech_choice 2) (null custom_tech_text))
    (progn
      (princ "\n请输入自定义技术要求内容: ")
      (setq custom_tech_text (getstring T))
    )
  )
  
  ;; 自动计算生成图号，格式为前缀/R-r0-口a0
  (setq drawing_no (strcat drawing_prefix "/R-" 
                           (rtos r0 2 4)     ; 曲率半径，最多显示四位小数
                           "-Φ" 
                           (rtos a0 2 2)))   ; 口径，最多显示两位小数
  
  ;; 自动获取当前日期
  (setq current_date (menucmd "M=$(edtime,$(getvar,date),YYYY/MO/DD)"))
  
  ;; 显示生成的图号信息
  (princ (strcat "\n生成的图号: " drawing_no))
  (princ (strcat "\n当前日期: " current_date))
  
 ;;================计算绘图所需的点========================
  (setq a1 (/ a0 2))                                ; 半口径
  (setq c_pt0 (list 0 0))                           ; 图形起始点
  (setq sag (- r0 (sqrt (- (* r0 r0) (* a1 a1)))))  ; 矢高计算
  (setq l_pt1 (list (- a1) 0))                          ; 左侧圆弧起点1
  (setq r_pt1 (list a1 0))                           ; 右侧圆弧起点1
  (setq c_pt1 (list 0 (- sag)))                     ; 圆弧顶点1
  (setq l_pt2 (list (- 0.5 (+ a1 t0)) 0))             ; 左侧倒角点2
  (setq r_pt2 (list (- (+ a1 t0) 0.5) 0))              ; 右侧倒角点2
  (setq l_pt3 (list (- (+ a1 t0)) (- 0.5)))              ; 左侧倒角点3
  (setq r_pt3 (list (+ a1 t0) (- 0.5)))              ; 右侧倒角点3
  (setq l_pt4 (list (- (+ a1 t0)) (- (+ sag 2.5))))         ; 平台左侧点4
  (setq r_pt4 (list (+ a1 t0) (- (+ sag 2.5))))     ; 平台右侧点4
  (setq l_pt5 (list (- 0.5 (+ a1 t0)) (- (+ sag 3))))         ; 平台左侧倒角点5
  (setq r_pt5 (list (- (+ a1 t0) 0.5) (- (+ sag 3))))     ; 平台右侧倒角点5
  (setq l_pt6 (list (- 5) (- (+ sag 3))))         ; 脖子上端左侧点6
  (setq r_pt6 (list 5 (- (+ sag 3))))             ; 脖子上端右侧点6
  (setq l_pt7 (list (- 5) (- (+ sag 8))))         ; 脖子下端左侧点7
  (setq r_pt7 (list 5 (- (+ sag 8))))             ; 脖子下端右侧点7
  (setq l_pt8 (list (- 8.5) (- (+ sag 8))))         ; 柄上端左侧倒角点8
  (setq r_pt8 (list 8.5 (- (+ sag 8))))             ; 柄上端右侧倒角点8
  (setq l_pt9 (list (- 9) (- (+ sag 8.5))))         ; 柄上端左侧倒角点9
  (setq r_pt9 (list 9 (- (+ sag 8.5))))             ; 柄上端右侧倒角点9
  (setq l_pt10 (list (- 9) (- (+ (+ sag 7.5) b0))))         ; 柄下端左侧倒角点10
  (setq r_pt10 (list 9 (-(+ (+ sag 7.5) b0))))             ; 柄下端右侧倒角点10
  (setq l_pt11 (list (- 8.5) (- (+ (+ sag 8) b0))))         ; 柄下端左侧倒角点11
  (setq r_pt11 (list 8.5 (-(+ (+ sag 8) b0))))             ; 柄下端右侧倒角点11
  (setq l_pt12 (list (- 3) (- (+ (+ sag 8) b0))))         ; R3圆弧左侧点12
  (setq r_pt12 (list 3 (-(+ (+ sag 8) b0))))             ; R3圆弧左侧点12
  (setq c_pt2 (list 0 (-(+ (+ sag 5) b0))))             ; R3圆弧顶点2
  (setq q_pt1 (list 0 3))                          ; 中心线点1
  (setq q_pt2 (list 0 (-(+ (+ sag 11) b0))))        ; 中心线点2
  (setq c_pt3 (list 0 (sqrt (- (* r0 r0) (* a1 a1)))))               ; 圆心点3
  (setq q_pt3 (list (- 5) (- (+ sag 10))))        ; 剖面线点3
  (setq q_pt4 (list 5 (- (+ sag 10))))        ; 剖面线点4

  
  ;;============绘制图形=============
  ;; 切换到轮廓线图层
  (setvar "clayer" "轮廓线")
  ;; 缩放至合适绘图的视图
  (setq w1 (list -100 100)
	w2 (list 100 -100))
  (command "zoom" "w" w1 w2)
  
  ;; 绘制直线：r_pt1到l_pt1
  (command "line" r_pt1 l_pt1 "")  
  ;; 绘制圆弧：l_pt1到r_pt1，半径为r0
  (command "arc" l_pt1 "e" r_pt1 "r" r0)
  ;; 绘制直线：l_pt1到l_pt2
  (command "line" l_pt1 l_pt2 "")
  ;; 绘制直线：l_pt2到l_pt3
  (command "line" l_pt2 l_pt3 "")
  ;; 绘制直线：l_pt3到l_pt4
  (command "line" l_pt3 l_pt4 "")
  ;; 绘制直线：l_pt4到l_pt5
  (command "line" l_pt4 l_pt5 "")
  ;; 绘制直线：l_pt5到l_pt6
  (command "line" l_pt5 l_pt6 "")
  ;; 绘制直线：l_pt6到l_pt7
  (command "line" l_pt6 l_pt7 "")
  ;; 绘制直线：l_pt7到l_pt8
  (command "line" l_pt7 l_pt8 "")
  ;; 绘制直线：l_pt8到l_pt9
  (command "line" l_pt8 l_pt9 "")
  ;; 绘制直线：l_pt9到l_pt10
  (command "line" l_pt9 l_pt10 "")
  ;; 绘制直线：l_pt10到l_pt11
  (command "line" l_pt10 l_pt11 "")
  ;; 绘制直线：r_pt1到r_pt2
  (command "line" r_pt1 r_pt2 "")
  ;; 绘制直线：r_pt2到r_pt3
  (command "line" r_pt2 r_pt3 "")
  ;; 绘制直线：r_pt3到r_pt4
  (command "line" r_pt3 r_pt4 "")
  ;; 绘制直线：r_pt4到r_pt5
  (command "line" r_pt4 r_pt5 "")
  ;; 绘制直线：r_pt5到r_pt6
  (command "line" r_pt5 r_pt6 "")
  ;; 绘制直线：r_pt6到r_pt7
  (command "line" r_pt6 r_pt7 "")
  ;; 绘制直线：r_pt7到r_pt8
  (command "line" r_pt7 r_pt8 "")
  ;; 绘制直线：r_pt8到r_pt9
  (command "line" r_pt8 r_pt9 "")
  ;; 绘制直线：r_pt9到r_pt10
  (command "line" r_pt9 r_pt10 "")
  ;; 绘制直线：r_pt10到r_pt11
  (command "line" r_pt10 r_pt11 "")  
  ;; 绘制直线：l_pt11到r_pt11
  (command "line" l_pt11 r_pt11 "")    
  ;; 绘制圆弧R3半圆：l_pt12到r_pt12
  (command "arc" r_pt12 "e" l_pt12 "r" "3")
  
  ;; 绘制中心线
  ;; 切换到中心线图层
  (setvar "clayer" "中心线")  
  ;; 绘制直线：q_pt1到q_pt2
  (command "line" q_pt1 q_pt2 "")

  
  ;;=============标注===============
  ;; 切换到标注线图层
  (setvar "clayer" "标注线")
  
  ;; 1. 标注圆弧的半径（标注l_pt1到r_pt1的圆弧，位置在左侧四等分点处） 
  ;; 关闭尺寸线强制 
  (setq old_dimtofl (getvar "dimtofl")) 
  (setvar "dimtofl" 0) 
  
  (setq arc_center c_pt3)  ; 正确的圆心坐标 
  
  ;; 计算圆弧四等分点（凹面圆弧，利用圆心与端点、最低点的角度） 
  (setq angL (angle arc_center l_pt1))                   ; 左端点相对圆心的角度 
  (setq angR (angle arc_center r_pt1))                   ; 右端点相对圆心的角度 
  (setq angB (angle arc_center c_pt1))                   ; 圆弧最低点相对圆心的角度 
  ;; 左侧四等分点：位于左端点与最低点之间 
  (setq left_quarter_angle (/ (+ angL angB) 2.0)) 
  (setq left_quarter_pt (polar arc_center left_quarter_angle r0)) 
  ;; 标注位置在左侧四等分点向右上方偏移0.5 
  (setq dim_pt1 (list (+ (car left_quarter_pt) 0.5) (+ (cadr left_quarter_pt) 0.5))) 
  (command "dimradius" left_quarter_pt dim_pt1) 
  ;; 2. 标注R3圆弧的半径（标注位置在右侧四等分点向左下方偏移0.5） 
  ;; 计算R3圆弧的圆心（圆心在l_pt10和r_pt10的中点，半径为3） 
  (setq r3_arc_center (list 0 (- (+ 5 t0 b0)))) 
  ;; 计算R3圆弧四等分点（凹面圆弧，利用圆心与端点、最低点的角度） 
  (setq angL_r3 (angle r3_arc_center l_pt10))              ; 左端点相对圆心的角度 
  (setq angR_r3 (angle r3_arc_center r_pt10))              ; 右端点相对圆心的角度 
  (setq angB_r3 (angle r3_arc_center c_pt2))              ; 圆弧最低点相对圆心的角度 
  ;; 右侧四等分点：位于右端点与最低点之间 
  (setq right_quarter_angle_r3 (/ (+ angR_r3 angB_r3) 2.0)) 
  (setq right_quarter_pt (polar r3_arc_center right_quarter_angle_r3 3)) 
  ;; 标注位置在右侧四等分点向左下方偏移0.5 
  (setq dim_pt2 (list (- (car right_quarter_pt) 0.5) (- (cadr right_quarter_pt) 0.5))) 
  (command "dimradius" right_quarter_pt dim_pt2) 
  ;; 恢复尺寸线强制 
  (setvar "dimtofl" old_dimtofl)

  ;; 3. 标注l_pt1到r_pt1的水平距离（向上偏移7.5）
  (setq dim_dy3 7.5)
  (setq dim_pt3 (list 0 dim_dy3))
  (command "dimlinear" l_pt1 r_pt1 "h" dim_pt3)

  ;; 4. 标注l_pt3到r_pt3的水平距离（向上偏移 11.5）
  (setq dim_dy4 11.5)
  (setq dim_pt4 (list 0 dim_dy4))
  (command "dimlinear" l_pt3 r_pt3 "h" dim_pt4)

  ;; 5. 标注l_pt7到r_pt7的水平距离（从r_pt7和l_pt7的中点向上偏移1）
  (setq dim_dy5 1)
  (setq mid_pt57 (list (/ (+ (car l_pt7) (car r_pt7)) 2) (/ (+ (cadr l_pt7) (cadr r_pt7)) 2)))
  (setq dim_pt5 (list (car mid_pt57) (+ (cadr mid_pt57) dim_dy5)))
  (command "dimlinear" l_pt7 r_pt7 "h" dim_pt5)
  
  ;; 6. 标注l_pt10到r_pt10的水平距离（从两点的中点向下偏移11.5）
  (setq dim_dy6 (- 11.5))
  (setq mid_pt610 (list (/ (+ (car l_pt10) (car r_pt10)) 2) (/ (+ (cadr l_pt10) (cadr r_pt10)) 2)))
  (setq dim_pt6 (list (car mid_pt610) (+ (cadr mid_pt610) dim_dy6)))
  (command "dimlinear" l_pt10 r_pt10 "h" dim_pt6)

  ;; 7. 标注r_pt2到r_pt5的垂直距离（向右偏移5.5）
  (setq dim_pt7 (list (+ (car r_pt2) 5.5) (/ (+ (cadr r_pt2) (cadr r_pt5)) 2)))
  (command "dimlinear" r_pt2 r_pt5 "v" dim_pt7)
  
  ;; 8. 标注r_pt8到r_pt11的垂直距离（r_pt1向右偏移10.5）
  (setq dim_pt8 (list (+ (car r_pt8) 10.5) (/ (+ (cadr r_pt8) (cadr r_pt11)) 2)))
  (command "dimlinear" r_pt8 r_pt11 "v" dim_pt8)
  
  ;; 9. 标注r_pt2到r_pt11的垂直距离（判断dim_pt7和dim_pt8谁更偏右，再从该位置向右偏移5.5）（将尺寸保留两位小数）
  (setq old_dimdec (getvar "dimdec"))
  (setvar "dimdec" 1)
  (setq dim_dx7 (car dim_pt7))
  (setq dim_dx8 (car dim_pt8))
  (if (> dim_dx7 dim_dx8)
    (setq dim_pt9 (list (+ dim_dx7 5.5) (/ (+ (cadr r_pt2) (cadr r_pt11)) 2)))
    (setq dim_pt9 (list (+ dim_dx8 5.5) (/ (+ (cadr r_pt2) (cadr r_pt11)) 2)))
  )
  (command "dimlinear" r_pt2 r_pt11 "v" dim_pt9)
  (setvar "dimdec" old_dimdec)

  ;; 10. 标注R3圆弧顶点c_pt2和r_pt11的垂直距离（向右偏移5.5）
  (setq dim_pt10 (list (+ (car r_pt11) 5.5) (/ (+ (cadr c_pt2) (cadr r_pt11)) 2)))
  (command "dimlinear" c_pt2 r_pt11 "v" dim_pt10)
  
  ;;=============图案填充===============
  ;; 切换到剖面线图层
  (setvar "clayer" "剖面线")
  
  ;; 使用ANSI31图案填充，内部点为q_pt3和q_pt4
  (command "-hatch" "p" "ANSI31" "1" "" q_pt3 q_pt4 "")
  
  ;; 切换回标注线图层
  (setvar "clayer" "标注线")

  ;;==============结束前调整===========
  ;; 缩放至合适视图
  (command "zoom" "all")
  
  ;;============绘制仰视图=============
  ;; 计算仰视图中心位置
  ;; 主视图最低点是标注4的位置（l_pt10和r_pt10的中点向下偏移11.5mm）
  (setq main_view_lowest_point (list (/ (+ (car l_pt10) (car r_pt10)) 2) 
                                     (- (/ (+ (cadr l_pt10) (cadr r_pt10)) 2) 11.5)))
  
  ;; 计算俯视图半径
  (setq top_view_radius (+ (/ a0 2) t0))
  
  ;; 仰视图中心点：距离主视图最低点大于俯视图半径+5mm
  (setq elevation_view_center (list (car main_view_lowest_point) 
                                    (- (cadr main_view_lowest_point) 
                                       (+ top_view_radius 5))))
  
  ;; 切换到轮廓线图层绘制仰视图
  (setvar "clayer" "轮廓线")
  
  ;; 绘制四个同心圆
  ;; 1. 半径3mm的圆
  (command "circle" elevation_view_center 3)
  (setq r3_circle_ent (entlast))
  
  ;; 2. 从弦左端点到弦右端点的圆弧（替代原来的半径9mm圆）
  ;; 计算弦的位置（距离圆心8mm）
  (setq chord_distance 8)  ; 弦距离圆心的垂直距离
  (setq chord_radius 9)    ; 圆的半径
  
  ;; 计算弦长（勾股定理）
  (setq half_chord_length (sqrt (- (* chord_radius chord_radius) (* chord_distance chord_distance))))
  
  ;; 计算弦的两个端点
  (setq chord_y (+ (cadr elevation_view_center) chord_distance))  ; 弦的Y坐标（圆心上方8mm）
  (setq chord_start (list (- (car elevation_view_center) half_chord_length) chord_y))
  (setq chord_end (list (+ (car elevation_view_center) half_chord_length) chord_y))
  
  ;; 计算圆弧的起始角度和结束角度（弦下方的圆弧）
  ;; 起始角度：弦左端点相对于圆心的角度
  (setq start_angle (atan (/ (- (cadr chord_start) (cadr elevation_view_center)) 
                           (- (car chord_start) (car elevation_view_center)))))
  ;; 结束角度：弦右端点相对于圆心的角度
  (setq end_angle (atan (/ (- (cadr chord_end) (cadr elevation_view_center)) 
                         (- (car chord_end) (car elevation_view_center)))))
  
  ;; 绘制弦下方的圆弧（从弦左端点到弦右端点）
  (command "arc" "c" elevation_view_center chord_start chord_end)
  
  ;; 3. 半径(a0/2+t0-0.5)的圆
  (setq circle_radius_3 (- top_view_radius 0.5))
  (command "circle" elevation_view_center circle_radius_3)
  
  ;; 4. 半径(a0/2+t0)的圆
  (command "circle" elevation_view_center top_view_radius)
  
  ;; 绘制仰视图中心线
  (setvar "clayer" "中心线")
  
  ;; 水平中心线
  (setq h_line_start (list (- (car elevation_view_center) (+ top_view_radius 5)) 
                           (cadr elevation_view_center)))
  (setq h_line_end (list (+ (car elevation_view_center) (+ top_view_radius 5)) 
                         (cadr elevation_view_center)))
  (command "line" h_line_start h_line_end "")
  
  ;; 垂直中心线
  (setq v_line_start (list (car elevation_view_center) 
                           (- (cadr elevation_view_center) (+ top_view_radius 5))))
  (setq v_line_end (list (car elevation_view_center) 
                         (+ (cadr elevation_view_center) (+ top_view_radius 5))))
  (command "line" v_line_start v_line_end "")
  
  ;; 绘制水平弦（使用前面计算好的弦端点）
  (setvar "clayer" "轮廓线")
  (command "line" chord_start chord_end "")
  
  ;; 标注弦距离圆心的垂直距离
  (setvar "clayer" "标注线")
  
  ;; 标注位置：在弦的右侧，向右偏移最大圆半径+5.5mm
  (setq chord_dim_x (+ (car elevation_view_center) top_view_radius 5.5))  ; 最大圆半径+5.5mm
  (setq chord_dim_pt (list chord_dim_x (/ (+ (cadr elevation_view_center) chord_y) 2)))
  
  ;; 标注弦的右端点到圆心的垂直距离
  (command "dimlinear" chord_start elevation_view_center "v" chord_dim_pt)
  
  ;; 仰视图其他标注
  (setvar "clayer" "标注线")
  
  ;; 标注R3圆直径（半径3mm的圆）
  (setq r3_radius 3)
  ;; 标注位置：向左上方偏移0.5
  (setq r3_dim_pt (list (- (car elevation_view_center) 0.5) 
                        (+ (cadr elevation_view_center) r3_radius 0.5)))
  ;; 直接对刚创建的圆实体标注，避免进入“选择圆弧或圆”的交互模式
  (if r3_circle_ent
    (command "dimdiameter" r3_circle_ent r3_dim_pt)
    (princ "\n警告: 未找到R3圆实体，跳过直径标注。")
  )
  
  ;;============切换到图纸布局=============
  (setup_layout_and_titleblock)

  ;; 缩放至合适视图
  (command "zoom" "all")
  
  ;; 恢复原始系统变量
  (setvar "osmode" old_osmode)
  (setvar "cmdecho" old_cmdecho)
  (setvar "orthomode" old_orthomode)
  (setvar "clayer" old_clayer)
  (setvar "attdia" old_attdia)
  (setvar "dimtofl" old_dimtofl)
  
  ;; 程序结束提示
  (princ (strcat "\n=== " product_name " 绘制完成！ ==="))
  (princ (strcat "\n图号: " drawing_no))
  (princ (strcat "\n材料: " material))
  (princ)
)


;;主程序中调用的程序：


;;==========================================
;; 检查布局是否存在
;;==========================================
(defun layout_exists (layout_name)
  (vl-load-com)
  (setq acad_doc (vla-get-activedocument (vlax-get-acad-object)))
  (setq exists nil)
  (vlax-for layout (vla-get-layouts acad_doc)
    (if (= (strcase (vla-get-name layout)) (strcase layout_name))
      (setq exists T)
    )
  )
  exists
)

;;==========================================
;; 设置图框属性值
;;==========================================
(defun set_attributes_of_titleblock ()
  ;; 设置A4图框块的属性值

  ;; 获取最后插入的块（图框）
  (setq block_ent (entlast))

  ;; 确保是插入的块
  (if (and block_ent 
           (= (cdr (assoc 0 (entget block_ent))) "INSERT")
           (= (cdr (assoc 2 (entget block_ent))) "A4图框"))
    (progn
      ;; 遍历块的所有子实体，找到属性并设置值
      (setq next_ent (entnext block_ent))
      (while next_ent
        (setq ent_data (entget next_ent))
        
        ;; 检查是否为属性定义
        (if (= (cdr (assoc 0 ent_data)) "ATTRIB")
          (progn
            (setq tag_name (cdr (assoc 2 ent_data)))  ; 属性标记
            
            ;; 根据属性标记设置对应的值
            (cond
              ((or (wcmatch tag_name "*名称*") 
                   (wcmatch tag_name "*name*"))
               (setq new_value product_name))
              
              ((or (wcmatch tag_name "*材料*") 
                   (wcmatch tag_name "*material*"))
               (setq new_value material))
              
              ((or (wcmatch tag_name "*图号*") 
                   (wcmatch tag_name "*drawing*"))
               (setq new_value drawing_no))
              
              ((or (wcmatch tag_name "*日期*") 
                   (wcmatch tag_name "*date*"))
               (setq new_value current_date))
              
              ((or (wcmatch tag_name "*比例*") 
                   (wcmatch tag_name "*scale*"))
               (setq new_value scale_text))
              
              (t
               ;; 对于其他属性，保持默认值
               (princ (strcat "\n保持属性默认值: " tag_name))
               ;; 不修改该属性，保持原值
               )
            )
            
            ;; 更新实体
            (entupd next_ent)
          )
        )
        
        (setq next_ent (entnext next_ent))
      )
      
      ;; 更新块引用
      (entupd block_ent)
      
      (princ "\n图框属性设置完成。")
    )
    (princ "\n警告: 未找到A4图框图块，无法设置属性。")
  )
)

;;==========================================
;; 设置布局和图框函数（使用现有布局和块）
;;==========================================
(defun setup_layout_and_titleblock ()
  ;; 切换到图纸空间
  (if (vl-catch-all-error-p (vl-catch-all-apply 'setvar (list "tilemode" 0)))
    (progn
      (princ "\n警告: tilemode 切换失败，尝试使用 pspace。")
      (command "pspace")
    )
  )
  
  ;; 检查布局"A4图纸"是否存在
  (if (layout_exists "A4图纸")
    (progn
      ;; 切换到"A4图纸"布局
      (command "layout" "set" "A4图纸")
      
      ;; 等待布局切换完成
      (while (> (getvar "CMDACTIVE") 0)
        (command "")
      )
      
      ;; 检查并插入"A4图框"块
      (if (tblsearch "BLOCK" "A4图框")
        (progn
          ;; 插入图框块（使用标准比例1:1）
          (setq titleblock_origin '(0 0))
          (command "insert" "A4图框" titleblock_origin "1" "1" "0")
          
          ;; 等待插入完成
          (while (> (getvar "CMDACTIVE") 0)
            (command "")
          )
          
          ;; 设置图框属性值
          (set_attributes_of_titleblock)
        )
        (progn
          (princ "\n警告: 未找到'A4图框'块，无法插入标准图框。")
        )
      )
      
      ;; 创建简单视口（固定比例1:1）
      (create_simple_viewport)
    )
    (progn
      (princ "\n警告: 布局'A4图纸'不存在。")
      ;; 保持在模型空间
      (setvar "tilemode" 1)
    )
  )
)

;;==========================================
;; 创建简单视口（固定比例1:1）
;;==========================================
(defun create_simple_viewport ()
  ;; 创建视口，然后设置比例为1:1
  ;; 使用标准视口位置和大小
  
  (setq vp_center (list 5 15))  ; A4图纸中心
  (setq vp_width 250)  ; 视口宽度
  (setq vp_height 180) ; 视口高度
  
  ;; 创建视口
  (command "mview" vp_center (list (+ (car vp_center) vp_width) 
                                   (+ (cadr vp_center) vp_height)))
  
  ;; 等待命令完成
  (while (> (getvar "CMDACTIVE") 0)
    (command "")
  )
  ;; 将视口对象移动到“视口”图层
  (setq vp_ent (entlast))
  (command "change" vp_ent "" "p" "la" "视口" "")
  
  ;; 进入模型空间设置比例
  (command "mspace")
  
  ;; 计算整个图形的中心位置
  ;; 主视图中心：X坐标为0，Y坐标为l_pt10和r_pt10中点的Y坐标
  (setq main_view_center_y (/ (+ (cadr l_pt10) (cadr r_pt10)) 2))
  
  ;; 仰视图中心：已经计算好的elevation_view_center
  ;; 整个图形的中心：主视图和仰视图的中间位置
  (setq overall_center_x 0)  ; X坐标保持为0（对称图形）
  (setq overall_center_y (/ (+ main_view_center_y (cadr elevation_view_center)) 2))
  (setq overall_center (list overall_center_x overall_center_y))
  
  ;; 计算图形的最大范围（用于缩放）
  ;; 主视图最高点：q_pt1 (0, 3)
  ;; 仰视图最低点：仰视图中心Y坐标减去最大圆半径
  (setq main_view_top_y 3)
  (setq elevation_view_bottom_y (- (cadr elevation_view_center) (+ (/ a0 2) t0)))
  
  ;; 计算图形总高度
  (setq total_height (- main_view_top_y elevation_view_bottom_y))
  
  ;; 居中显示图形，以整个图形的中心为中心
  (command "zoom" "c" overall_center (strcat (rtos (* total_height 1.2) 2 2)))
  
  ;; 设置视口比例为1:1
  (command "zoom" "1xp")
  
  ;; 返回图纸空间
  (command "pspace")
  
  ;;添加技术要求
  (add_technical_requirements)
)


;;==========================================
;; 设置图框属性值
;;==========================================
(defun set_attributes_of_titleblock ()
  ;; 设置A4图框块的属性值

  ;; 获取最后插入的块（图框）
  (setq block_ent (entlast))

  ;; 确保是插入的块
  (if (and block_ent 
           (= (cdr (assoc 0 (entget block_ent))) "INSERT")
           (= (cdr (assoc 2 (entget block_ent))) "A4图框"))
    (progn
      ;; 遍历块的所有子实体，找到属性并设置值
      (setq next_ent (entnext block_ent))
      (while next_ent
        (setq ent_data (entget next_ent))
        
        ;; 检查是否为属性定义
        (if (= (cdr (assoc 0 ent_data)) "ATTRIB")
          (progn
            (setq tag_name (cdr (assoc 2 ent_data)))  ; 属性标记
            
            ;; 根据属性标记设置对应的值
            (cond
              ((or (wcmatch tag_name "*名称*") 
                   (wcmatch tag_name "*NAME*")
                   (wcmatch tag_name "*name*"))
               (entmod (subst (cons 1 product_name) (assoc 1 ent_data) ent_data)))
              
              ((or (wcmatch tag_name "*图号*") 
                   (wcmatch tag_name "*NO*")
                   (wcmatch tag_name "*Drawing*"))
               (entmod (subst (cons 1 drawing_no) (assoc 1 ent_data) ent_data)))
              
              ((or (wcmatch tag_name "*材料*") 
                   (wcmatch tag_name "*MATERIAL*")
                   (wcmatch tag_name "*material*"))
               (entmod (subst (cons 1 material) (assoc 1 ent_data) ent_data)))
              
              ((or (wcmatch tag_name "*比例*") 
                   (wcmatch tag_name "*SCALE*")
                   (wcmatch tag_name "*scale*"))
               (entmod (subst (cons 1 "1:1") (assoc 1 ent_data) ent_data)))
              
              ((or (wcmatch tag_name "*日期*") 
                   (wcmatch tag_name "*DATE*")
                   (wcmatch tag_name "*date*"))
               (entmod (subst (cons 1 current_date) (assoc 1 ent_data) ent_data)))
              
              ((or (wcmatch tag_name "*修改日期*") 
                   (wcmatch tag_name "*MODIFY*")
                   (wcmatch tag_name "*modify*"))
               (entmod (subst (cons 1 current_date) (assoc 1 ent_data) ent_data)))
               ;; 其他未设置的属性保持默认值
              (T
               (princ (strcat "\n保持属性默认值: " tag_name))
               ;; 不修改该属性，保持原值
               )
            )
            
            ;; 更新实体数据
            (entupd next_ent)
          )
        )
        
        (setq next_ent (entnext next_ent))
      )
      
      ;; 更新块引用
      (entupd block_ent)
      
      (princ "\n图框属性设置完成。")
    )
    (princ "\n警告: 未找到A4图框图块，无法设置属性。")
  )
)

;;==========================================
;; 添加技术要求多行文字
;;==========================================
(defun add_technical_requirements ()
  ;; 确保在图纸空间
  (command "pspace")

  ;;将文字样式设置成"Standard"
  (command "-style" "Standard" "" "" "" "" "" "")

  ;;将图层设置成标注层
  ;(setvar "clayer" "标注层")

  ;; 定义文字区域的两个角点
  (setq text_corner1 '(-5 50))
  (setq text_corner2 '(45 0))

  ;; 根据用户选择确定技术要求内容
  (setq tech_text "")
  (if (= tech_choice 1)
    ;; 使用默认技术要求
    (setq tech_text "技术要求：\n1.去除所有飞边毛刺，锐边倒钝\n2.倒角0.5*45°\n3.按图号打标")
    ;; 使用自定义技术要求
    (setq tech_text (strcat "技术要求：\n" custom_tech_text))
  )

  ;; 创建多行文字
  (command "mtext" text_corner1 text_corner2 tech_text "")
)

(defun c:xba () (xba nil nil nil nil nil nil nil) (princ))
