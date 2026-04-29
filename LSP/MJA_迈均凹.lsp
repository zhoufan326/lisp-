(defun mja (r0 a0 t0 save_path /
               old_osmode old_cmdecho old_orthomode old_clayer old_attdia product_name material drawing_prefix)
  ;;===============定义程序名称和参数：使用defun函数定义程序，并声明局部变量===============
  (vl-load-com) ; 加载ActiveX支持
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
  (setvar "osmode" 0) ;对象捕捉
  (setvar "cmdecho" 0) ;回显提示和输入
  (setvar "orthomode" 0) ;正交模式
  (setvar "attdia" 0) ;关闭属性对话框，以便程序控制

  ;;=================工装类型选择===================
   

  (princ "\n=== 迈均凹工装绘图程序 ===")
  
  ;; 固定工装类型为抛光模基模
  (setq product_name "抛光模基模")
  (setq material "LY12")
  (setq drawing_prefix "XPMJM")
  ;;验证获取的工装名称，材料，图号前缀
  (princ (strcat "\n=== " product_name " ==="))
  (princ (strcat "\n材料: " material))
  (princ (strcat "\n图号前缀: " drawing_prefix))

  ;;=================获取用户输入：使用函数获取用户输入的参数=========================
  (princ "\n=== 迈均凹工装绘图程序 ===")
  (if (null r0) (setq r0 (getdist "\n请输入曲率半径: ")))
  (if (null a0) (setq a0 (getdist "\n请输入口径(直径): ")))
  (if (null t0) (setq t0 (getdist "\n请输入边厚: ")))

  ;; 验证输入参数的合理性
  (if (or (null r0) (null a0) (null t0) (<= r0 0) (<= a0 45) (<= t0 0)) 
    (progn 
      (princ "\n参数值无效：曲率半径和厚度必须大于0，口径必须大于45，程序终止。")
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

  ;; 计算矢高sag
  (setq a1 (/ a0 2)) ; 半口径
  (setq sag (- r0 (sqrt (- (* r0 r0) (* a1 a1))))) ; 矢高计算

  ;; 计算最小边厚要求（sag+5）
  (setq min_t0 (+ sag 5))
  ;; 验证边厚是否满足最小要求
  (if (< t0 min_t0) 
    (progn 
      (princ (strcat "\n边厚太小，最小边厚要求为: " (rtos min_t0 2 2) "，已使用最小边厚。"))
      (setq t0 min_t0)
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
  (setq drawing_no (strcat drawing_prefix 
                           "／R"
                           (rtos r0 2 4) ; 曲率半径，最多显示四位小数
                           "-Φ"
                           (rtos a0 2 2) ; 口径，最多显示两位小数
                   )
  )

  ;; 自动获取当前日期
  (setq current_date (menucmd "M=$(edtime,$(getvar,date),YYYY/MO/DD)"))

  ;; 显示生成的图号信息
  (princ (strcat "\n生成的图号: " drawing_no))
  (princ (strcat "\n当前日期: " current_date))

  ;;================计算绘图所需的点========================
  (setq c_pt0 (list 0 0)) ; 图形起点
  (setq c_pt1 (list 0 (- sag))) ; 圆弧最低点1
  (setq l_pt1 (list (- a1) 0)) ; 左侧圆弧端点1
  (setq r_pt1 (list a1 0)) ; 右侧圆弧端点1
  (setq l_pt2 (list (- (+ a1 1.5)) 0)) ; 左侧倒角点2
  (setq r_pt2 (list (+ a1 1.5) 0)) ; 右侧倒角点2
  (setq l_pt3 (list (- (+ a1 2)) (- 0.5))) ; 左侧倒角点3
  (setq r_pt3 (list (+ a1 2) (- 0.5))) ; 右侧倒角点3
  (setq l_pt4 (list (- (+ a1 2)) (- 0.5 t0))) ; 左侧倒角点4
  (setq r_pt4 (list (+ a1 2) (- 0.5 t0))) ; 右侧倒角点4
  (setq l_pt5 (list (- (+ a1 2)) (- t0))) ; 左侧倒角点5
  (setq r_pt5 (list (+ a1 2) (- t0))) ; 右侧倒角点5
  (setq l_pt6 (list (- 24.5) (- t0))) ; 左侧延伸点6
  (setq r_pt6 (list 24.5 (- t0))) ; 右侧延伸点6
  (setq l_pt7 (list (- 24.5) (- 35))) ; 左侧延伸点7
  (setq r_pt7 (list 24.5 (- 35))) ; 右侧延伸点7
  (setq c_pt2 (list 0 (sqrt (- (* r0 r0) (* a1 a1))))) ; 圆弧圆心
  (setq c_pt3 (list 0 (- 35))) ; 块插入点
  (setq q_pt1 (list 0 3)) ; 中心线点1
  (setq q_pt2 (list 0 -63)) ; 中心线点2

  ;; 计算圆弧四等分点（凹面圆弧，利用圆心与端点、最低点的角度）
  (setq angL (angle c_pt2 l_pt1)) ; 左端点相对圆心的角度
  (setq angR (angle c_pt2 r_pt1)) ; 右端点相对圆心的角度
  (setq angB (angle c_pt2 c_pt1)) ; 圆弧最低点相对圆心的角度
  ;; 左侧四等分点：位于左端点与最低点之间
  (setq l_pt8 (polar c_pt2 (/ (+ angL angB) 2.0) r0)) ; 左侧四等分点4
  ;; 右侧四等分点：位于右端点与最低点之间
  (setq r_pt8 (polar c_pt2 (/ (+ angR angB) 2.0) r0)) ; 右侧四等分点4

  ;; [计算其他绘图所需的关键点]
  (setq q_pt3 (list 0 (- t0))) ; 图案填充点3
  (setq q_pt4 (list 11.5 -45)) ; 图案填充点4
  (setq q_pt5 (list -11.5 -45)) ; 图案填充点5
  (setq q_pt6 (list 24 -60)) ; 总高标注点6
  (setq q_pt7 (list a1 11)) ; 形位公差点7

  ;;============绘制图形========================
  ;; 切换到轮廓线图层
  (setvar "clayer" "轮廓线")

  ;; 插入块"迈均单玉M24"，插入点为c_pt3
  (command "insert" "迈均单玉M24" c_pt3 "1" "1" "0")
  ;; 绘制圆弧：起点l_pt1，终点r_pt1，半径r0
  (command "arc" l_pt1 "e" r_pt1 "r" r0)
  ;; 绘制直线：l_pt1到r_pt1
  (command "line" l_pt1 r_pt1 "")
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
  ;; 插入块"同轴度-0.1-A"，插入点为q_pt7
  (command "insert" "同轴度-0.1-A" q_pt7 "1" "1" "0")

  ;;=============标注===============
  ;; 切换到标注线图层
  (setvar "clayer" "标注线")

  ;; 1. 标注圆弧的半径（位置在l_pt8向右上方偏移0.5）
  ;; 关闭尺寸线强制
  (setq old_dimtofl (getvar "dimtofl"))
  (setvar "dimtofl" 0)
  (setq dim_pt1 (list (+ (car l_pt8) 0.5) (+ (cadr l_pt8) 0.5)))
  (command "dimradius" l_pt8 dim_pt1)
  ;; 如果命令仍在活动（表示需要用户选择），等待用户完成选择
  (while (> (getvar "CMDACTIVE") 0) 
    (command pause)
  )
  (setvar "dimtofl" old_dimtofl)
  (princ (strcat "\n=== 圆弧标注完成！ ==="))

  ;; 2. 标注l_pt1到r_pt1的水平距离（向上偏移11）
  (setq dim_dy2 11)
  (setq dim_pt2 (list 0 dim_dy2))
  (command "dimlinear" l_pt1 r_pt1 "h" "t" "%%c<>" dim_pt2)

  ;; 3. 标注l_pt3到r_pt3的垂直距离（向上偏移16）
  (setq dim_pt3 (list (/ (+ (car l_pt3) (car r_pt3)) 2) (+ (cadr l_pt3) 16)))
  (command "dimlinear" l_pt3 r_pt3 "h" "t" "%%c<>" dim_pt3)

  ;; 4. 标注r_pt2到r_pt5的垂直距离（从r_pt2向右偏移5.5）
  (setq dim_dx4 (+ (car r_pt2) 5.5))
  (setq dim_pt4 (list dim_dx4 (/ (+ (cadr r_pt2) (cadr r_pt5)) 2)))
  ;; 保存当前标注精度设置
  (setq old_dimdec (getvar "dimdec"))
  (setvar "dimdec" 2) ;; 设置标注精度为两位小数
  (command "dimlinear" r_pt2 r_pt5 "v" "t" "<>" dim_pt4)
  ;; 恢复标注精度设置
  (setvar "dimdec" old_dimdec)

  ;; 5. 标注q_pt6到r_pt2的垂直距离（比较dim_dx4和58.5哪个更远，取更远的加5.5）
  (if (> dim_dx4 58.5) 
    (setq dim_pt5 (list (+ dim_dx4 5.5) (/ (+ (cadr q_pt6) (cadr r_pt2)) 2)))
    (setq dim_pt5 (list (+ 58.5 5.5) (/ (+ (cadr q_pt6) (cadr r_pt2)) 2)))
  )
  (command "dimlinear" q_pt6 r_pt2 "v" dim_pt5)

  ;;=============图案填充===============
  ;; 切换到剖面线图层
  (setvar "clayer" "剖面线")

  ;; 使用ANSI31图案填充，内部点为q_pt3、q_pt4、q_pt5
  (command "-hatch" "p" "ANSI31" "1" "" q_pt3 q_pt4 q_pt5 "")

  ;; 切换回标注线图层
  (setvar "clayer" "标注线")

  ;;=========== 绘制中心线============
  ;; 切换到中心线图层
  (setvar "clayer" "中心线")
  ;; 绘制直线：q_pt1到q_pt2
  (command "line" q_pt1 q_pt2 "")
  ;; 切换回标注线图层
  (setvar "clayer" "标注线")

  ;;==============结束前调整===========
  ;; 缩放至合适视图
  (command "zoom" "all")

  ;;============切换到图纸布局=============
  (setup_layout_and_titleblock save_path)

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

(defun c:mja () (mja nil nil nil nil) (princ))

;;==========================================
;; 主程序入口函数
;;==========================================

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
;; 设置布局和图框函数（使用现有布局和块）
;;==========================================
(defun setup_layout_and_titleblock (save_path) 
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
      (create_simple_viewport save_path)
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
(defun create_simple_viewport (save_path) 
  ;; 创建视口，然后设置比例为1:1
  ;; 使用标准视口位置和大小

  (setq vp_center (list 5 15)) ; A4图纸中心
  (setq vp_width 250) ; 视口宽度
  (setq vp_height 180) ; 视口高度

  ;; 创建视口
  (command "mview" 
           vp_center
           (list (+ (car vp_center) vp_width) 
                 (+ (cadr vp_center) vp_height)
           )
  )

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
  ;; 图形中心：X坐标为0，Y坐标为l_pt2和q_pt6中点的Y坐标
  (setq overall_center_x 0) ; X坐标保持为0（对称图形）
  (setq overall_center_y (/ (+ (cadr l_pt2) (cadr q_pt6)) 2))
  (setq overall_center (list overall_center_x overall_center_y))

  ;; 计算图形的最大范围（用于缩放）

  ;; 图形最高点：q_pt1 (0, 3)
  ;; 图形最低点：q_pt2 (0, -63)
  (setq main_view_top_y 3)
  (setq elevation_view_bottom_y -63)

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
  ;;自动保存和打印
  (auto_save save_path)
)

  ;;==========================================
  ;; 设置图框属性值
  ;;==========================================
(defun set_attributes_of_titleblock () 
  ;; 设置A4图框块的属性值

  ;; 获取最后插入的块（图框）
  (setq block_ent (entlast))

  ;; 确保是插入的块
  (if 
    (and block_ent 
         (= (cdr (assoc 0 (entget block_ent))) "INSERT")
         (= (cdr (assoc 2 (entget block_ent))) "A4图框")
    )
    (progn 
      ;; 遍历块的所有子实体，找到属性并设置值
      (setq next_ent (entnext block_ent))
      (while next_ent 
        (setq ent_data (entget next_ent))

        ;; 检查是否为属性定义
        (if (= (cdr (assoc 0 ent_data)) "ATTRIB") 
          (progn 
            (setq tag_name (cdr (assoc 2 ent_data))) ; 属性标记

            ;; 根据属性标记设置对应的值
            (cond 
              ((or (wcmatch tag_name "*名称*") 
                   (wcmatch tag_name "*NAME*")
                   (wcmatch tag_name "*name*")
               )
               (entmod (subst (cons 1 product_name) (assoc 1 ent_data) ent_data))
              )

              ((or (wcmatch tag_name "*图号*") 
                   (wcmatch tag_name "*NO*")
                   (wcmatch tag_name "*Drawing*")
               )
               (entmod (subst (cons 1 drawing_no) (assoc 1 ent_data) ent_data))
              )

              ((or (wcmatch tag_name "*材料*") 
                   (wcmatch tag_name "*MATERIAL*")
                   (wcmatch tag_name "*material*")
               )
               (entmod (subst (cons 1 material) (assoc 1 ent_data) ent_data))
              )

              ((or (wcmatch tag_name "*比例*") 
                   (wcmatch tag_name "*SCALE*")
                   (wcmatch tag_name "*scale*")
               )
               (entmod (subst (cons 1 "1:1") (assoc 1 ent_data) ent_data))
              )

              ((or (wcmatch tag_name "*日期*") 
                   (wcmatch tag_name "*DATE*")
                   (wcmatch tag_name "*date*")
               )
               (entmod (subst (cons 1 current_date) (assoc 1 ent_data) ent_data))
              )

              ((or (wcmatch tag_name "*修改日期*") 
                   (wcmatch tag_name "*MODIFY*")
                   (wcmatch tag_name "*modify*")
               )
               (entmod (subst (cons 1 current_date) (assoc 1 ent_data) ent_data))
              )
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

  ;; 使用默认技术要求
  (setq tech_text "技术要求：\n1.去除所有飞边毛刺，锐边倒钝\n2.倒角0.5*45°\n3.按图号打标")

  ;; 创建多行文字
  (command "mtext" text_corner1 text_corner2 tech_text "")
)

;;==========================================
;; 自动保存函数
;;==========================================
(defun auto_save (save_path)
  ;; 确保在图纸空间
  (command "pspace")

  ;; 获取保存路径（优先使用Python传递的路径）
  (setq base_dwg_path (if (and save_path (/= save_path "")) save_path (getvar "SAVEFILEPATH")))

  ;; 如果没有传递路径，使用默认路径
  (if (= base_dwg_path "")
    (setq base_dwg_path "P:\\AutoLISP_工装绘图项目\\工装绘图文件\\绘图文件")
  )

  ;; 创建保存路径
    ;; ??????????????????????????????
  (setq safe_drawing_no (vl-string-subst "／" "/" drawing_no))
  (setq safe_drawing_no (vl-string-subst "／" "\\" safe_drawing_no))

  (setq dwg_save_path (strcat base_dwg_path "/" safe_drawing_no ".dwg"))

  ;; 保存DWG文件
  (setq old_expert (getvar "EXPERT"))
  (setvar "EXPERT" 5) ; 静默覆盖现有文件
  (princ (strcat "\n正在保存DWG文件到: " dwg_save_path))
  (command "saveas" "" dwg_save_path)
  (setvar "EXPERT" old_expert)
  (setvar "USERS1" "SUCCESS") ; 设置成功标志位
)

  ;;==========================================
 

(defun c:mja () (mja nil nil nil nil) (princ))
