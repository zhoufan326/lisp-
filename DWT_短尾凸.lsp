(defun c:dwt (r0 a0 t0 tool_type /
               old_osmode old_cmdecho old_orthomode old_clayer old_attdia product_name material drawing_prefix)
  ;;===============定义程序名称和参数：使用defun函数定义程序，并声明局部变量===============
  (vl-load-com)  ; 加载ActiveX支持
  ;; 保存原始系统变量
  (setq old_osmode (getvar "osmode"))
  (setq old_cmdecho (getvar "cmdecho"))
  (setq old_orthomode (getvar "orthomode"))
  (setq old_clayer (getvar "clayer"))
  (setq old_attdia (getvar "attdia"))
  
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
    ;; 退出函数
    (princ)
  )
  
  ;; 设置新的系统变量
  (setvar "osmode" 0)       ;对象捕捉
  (setvar "cmdecho" 0)      ;回显提示和输入
  (setvar "orthomode" 0)    ;正交模式
  (setvar "attdia" 0)       ;关闭属性对话框，以便程序控制
  
  
  ;;=================工装类型选择===================
  (if (null tool_type)
    (progn
      (initget 1 "1 2 3 4 5")
      (setq tool_type (getkword "\n请选择工装类型: 1. 抛光模基模修盘 2. 抛光模修盘基模 3. 球面低抛细磨盘 4. 球面低抛粘盘 5. 球面低抛抛盘 "))
    )
  )
  
  ;; 根据工装类型设置参数
  (cond
    ((= tool_type "1")
     (setq product_name "抛光模基模修盘")
     (setq material "HT40-20")
     (setq drawing_prefix "GPMJX"))
    
    ((= tool_type "2")
     (setq product_name "抛光模修盘基模")
     (setq material "LY12")
     (setq drawing_prefix "GPMXJ"))
    
    ((= tool_type "3")
     (setq product_name "球面低抛细磨盘")
     (setq material "HT40-20")
     (setq drawing_prefix "QX"))
    
    ((= tool_type "4")
     (setq product_name "球面低抛粘盘")
     (setq material "LY12")
     (setq drawing_prefix "QZ"))
    
    ((= tool_type "5")
     (setq product_name "球面低抛抛盘")
     (setq material "LY12")
     (setq drawing_prefix "QP"))
    
    (T
     (princ "\n选择无效，程序终止。")
     (exit))
  )
  ;;验证获取的工装名称，材料，图号前缀
  (princ (strcat "\n=== " product_name " ==="))
  (princ (strcat "\n材料: " material))
  (princ (strcat "\n图号前缀: " drawing_prefix))
  
  ;;=================获取用户输入：使用函数获取用户输入的参数=========================
  (if (or (null r0) (null a0) (null t0))
    (progn
      (princ "\n=== 短尾M24凸工装绘图程序 ===")
      (if (null r0) (setq r0 (getdist "\n请输入曲率半径: ")))
      (if (null a0) (setq a0 (getdist "\n请输入口径(直径): ")))
      (if (null t0) (setq t0 (getdist "\n请输入边厚: ")))
    )
  )
  
  ;; 验证输入参数的合理性
  (if (or (<= r0 0) (<= a0 0) (<= t0 0))
    (progn
      (princ "\n参数值必须大于0，程序终止。")
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
  
  ;; 自动生成完整图号（格式：前缀/Rr0-Φa0）
  (setq drawing_no (strcat drawing_prefix "/R" 
                           (rtos r0 2 4)     ; 曲率半径，最多显示四位小数
                           "-Φ" 
                           (rtos a0 2 2)))   ; 口径，最多显示两位小数
  
  ;; 自动获取当前日期
  (setq current_date (menucmd "M=$(edtime,$(getvar,date),YYYY/MO/DD)"))
  
  ;; 显示生成的图号信息
  (princ (strcat "\n生成的图号: " drawing_no))
  (princ (strcat "\n当前日期: " current_date))
  
 ;;================计算绘图所需的点========================
  (setq a1 (/ a0 2))                                ; 实际半径
  (setq c_pt0 (list 0 0))                           ; 图形中心点
  (setq sag (- r0 (sqrt (- (* r0 r0) (* a1 a1)))))  ; 矢高计算
  (setq t_pt1 (list 0 (- (+ sag t0))))              ; 圆弧顶点1（直接计算y坐标）
  (setq l_pt1 (list (- (- a1 0.5)) 0))              ; 左侧倒角点1
  (setq r_pt1 (list (- a1 0.5) 0))                  ; 右侧倒角点1
  (setq c_pt1 (list 0 -0.5))                        ; 倒角中心点1
  (setq l_pt2 (list (- a1) -0.5))                   ; 左侧倒角点2
  (setq r_pt2 (list a1 -0.5))                       ; 右侧倒角点2
  (setq c_pt2 (list 0 (- t0)))                      ; 弦中心点2（c_pt0下方t0距离）
  (setq l_pt3 (list (- a1) (- t0)))                 ; 左侧圆弧点3
  (setq r_pt3 (list a1 (- t0)))                     ; 右侧圆弧点3
  (setq q_pt1 (list 15 14))                         ; 右侧图形最高点1
  (setq q_pt2 (list 15.5 0))                        ; 右侧连接点2
  (setq c_pt3 (list 0 (- (- (- sag) t0) 3)))        ; 中心线点3
  (setq c_pt4 (list 0 17))                          ; 中心线点4
  (setq h0 (- r0 sag))                              ; 圆心到弦的距离h0 = r0 - sag
  (setq c_pt5 (list 0 (+ (- t0) h0)))               ; 圆心点5（在弦c_pt2上方h0距离）
  
  ;; 计算圆弧四等分点（凹面圆弧，利用圆心与端点、最低点的角度）
  (setq angL (angle c_pt5 l_pt3))                   ; 左端点相对圆心的角度
  (setq angR (angle c_pt5 r_pt3))                   ; 右端点相对圆心的角度
  (setq angB (angle c_pt5 t_pt1))                   ; 圆弧最低点相对圆心的角度
  ;; 左侧四等分点：位于左端点与最低点之间
  (setq l_pt4 (polar c_pt5 (/ (+ angL angB) 2.0) r0))  ; 左侧四等分点4
  ;; 右侧四等分点：位于右端点与最低点之间
  ;(setq r_pt4 (polar c_pt5 (/ (+ angR angB) 2.0) r0))  ; 右侧四等分点4
  (setq ang1 (/ (+ angR angB) 2.0))
  (setq r_pt4(polar c_pt5 ang1 r0))
  
  ;; [计算其他绘图所需的关键点]
  (setq q_pt3 (list 1 (- t0)))                         ; 图案填充点3
  (setq q_pt4 (list 11.5 8.25))                        ; 图案填充点4

  
  ;;============绘制图形========================
  ;; 切换到轮廓线图层
  (setvar "clayer" "轮廓线")
  
  ;; 插入块"短尾M24"，插入点为c_pt0
  (command "insert" "短尾M24" c_pt0 "1" "1" "0")
  
  ;; 绘制直线：c_pt0到l_pt1
  (command "line" c_pt0 l_pt1 "")  
  ;; 绘制直线：l_pt1到l_pt2
  (command "line" l_pt1 l_pt2 "")
  ;; 绘制直线：l_pt2到c_pt1
  (command "line" l_pt2 c_pt1 "")
  ;; 绘制直线：l_pt2到l_pt3
  (command "line" l_pt2 l_pt3 "")
  ;; 绘制直线：l_pt3到c_pt2
  (command "line" l_pt3 c_pt2 "")
  ;; 绘制直线：q_pt2到r_pt1
  (command "line" q_pt2 r_pt1 "")
  ;; 绘制直线：l\r_pt1到r_pt2
  (command "line" r_pt1 r_pt2 "")
  ;; 绘制直线：r_pt2到r_pt3
  (command "line" r_pt2 r_pt3 "")  
  ;; 绘制圆弧：起点l_pt3，终点r_pt3，半径r0
  (command "arc" l_pt3 "e" r_pt3 "r" r0)
  ;;将圆弧存为e1图元
  ;(setq e1 (entlast))
  
  ;; 绘制中心线
  ;; 切换到中心线图层
  (setvar "clayer" "中心线")  
  ;; 绘制直线：c_pt3到c_pt4
  (command "line" c_pt3 c_pt4 "")

  
  ;;=============标注===============
  ;; 切换到标注线图层
  (setvar "clayer" "标注线")
  
  ;; 1. 标注圆弧的半径（位置在r_pt4向右下方偏移0.5）
  ;; 关闭尺寸线强制
  (setq old_dimtofl (getvar "dimtofl"))
  (setvar "dimtofl" 0)
  ;;打开对象捕捉
  ;(setvar "osmode" 512)
  (setq dim_pt5 (list (+ (car r_pt4) 0.5) (- (cadr r_pt4) 0.5)))
  ;;测试标注点的位置
  ;(command "line" r_pt4 dim_pt5 "")
  
  ;(command "dimradius" r_pt4 dim_pt5)
  (command "dimradius" r_pt4 "@0.5,-0.5")
  ;;关闭对象捕捉
  ;(setvar "osmode" 0)
  ;; 恢复尺寸线强制
  (setvar "dimtofl" old_dimtofl)
  (princ (strcat "\n=== 圆弧标注完成！ ==="))
  
  ;; 2. 标注l_pt3到r_pt3的水平距离（向下偏移 sag+11）
  (setq dim_dy1 (- 0 sag 11))
  (setq dim_pt1 (list 0 dim_dy1))
  (command "dimlinear" l_pt3 r_pt3 "h" "t" "%%c<>" dim_pt1)
  
  ;; 3. 标注r_pt1到r_pt3的垂直距离（向右偏移5.5）
  (setq dim_pt2 (list (+ (car r_pt1) 5.5) (/ (+ (cadr r_pt1) (cadr r_pt3)) 2)))
  (command "dimlinear" r_pt1 r_pt3 "v" dim_pt2)
  
  ;; 4. 标注q_pt1到r_pt1的垂直距离（r_pt1向右偏移10）
  (setq dim_pt3 (list (+ (car r_pt1) 10) (/ (+ (cadr q_pt1) (cadr r_pt1)) 2)))
  (command "dimlinear" q_pt1 r_pt1 "v" dim_pt3)
  
  ;; 5. 标注q_pt1到t_pt1的垂直距离（向右偏移 a1+18，尺寸两头加括号）
  (setq dim_dx4 (+ a1 18))
  (setq dim_pt4 (list dim_dx4 (/ (+ (cadr q_pt1) (cadr t_pt1)) 2)))
  (command "dimlinear" q_pt1 t_pt1 "v" "t" "(<>)" dim_pt4)
  
  
  
  ;;=============图案填充===============
  ;; 切换到剖面线图层
  (setvar "clayer" "剖面线")
  
  ;; 使用ANSI31图案填充，内部点为q_pt3和q_pt4
  (command "-hatch" "p" "ANSI31" "1" "" q_pt3 q_pt4 "")
  
  ;; 切换回标注线图层
  (setvar "clayer" "标注线")

  ;;==============形位公差和表面处理要求标注================
  ;; 仅当工装类型为1（抛光模基模修盘）和3（球面低抛细磨盘）时插入开槽指示箭头
  (if (or (= tool_type "1") (= tool_type "3"))
    (progn
      ;插入开槽指示箭头
      (command "insert" "开槽" l_pt4 "1" "1" "0")
    )
    ;; 工装类型不是1或3时，跳过开槽块插入
  )

  
  ;;==============结束前调整===========
  ;; 缩放至合适视图
  (command "zoom" "all")
  
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
  
  ;; 程序结束提示
  (princ (strcat "\n=== " product_name " 绘制完成！ ==="))
  (princ (strcat "\n图号: " drawing_no))
  (princ (strcat "\n材料: " material))
  (princ)
)



;;主程序中调用的程序：
;;==========================================
;; 添加技术要求多行文字
;;==========================================
(defun add_technical_requirements ()
  ;; 确保在图纸空间
  (command "pspace")

  ;;将文字样式设置成“Standard”
  (command "-style" "Standard" "" "" "" "" "" "")

  ;;将图层设置成标注层
  ;(setvar "clayer" "标注层")

  ;; 定义文字区域的两个角点
  (setq text_corner1 '(-5 50))
  (setq text_corner2 '(45 0))

  ;; 根据工装类型确定技术要求内容
  (setq tech_text "")
  (if (or (= tool_type "1") (= tool_type "3"))
    ;; 工装类型为1和3时的内容
    (setq tech_text "技术要求：\n1.去除所有飞边毛刺，锐边倒钝\n2.倒角0.5*45°\n3.开槽处开三道V型槽，槽宽2，槽深2， 槽距渐宽\n4按图号打标")
    ;; 工装类型为2、4和5时的内容
    (setq tech_text "技术要求：\n1.去除所有飞边毛刺，锐边倒钝\n2.倒角0.5*45°\n3.按图号打标")
  )

  ;; 创建多行文字
  (command "mtext" text_corner1 text_corner2 tech_text "")
)

;;==========================================
;; 设置布局和图框函数（使用现有布局和块）
;;==========================================
(defun setup_layout_and_titleblock ()
  ;; 切换到图纸空间
  (setvar "tilemode" 0)
  
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
  
  ;; 居中显示图形
  (command "zoom" "c" '(0 0) "100")
  
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


