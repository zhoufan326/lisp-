(defun c:hello-world (name)
  "Prints a hello world message to the console."
  (princ (strcat "\nHello, " name "!"))
  (princ)
)

(defun xba-test (x y is-fast-flag)
  "A test function with multiple parameters including a flag.
   x: The x coordinate.
   y: The y coordinate.
   is-fast-flag: Boolean flag for speed."
  (if is-fast-flag
      (princ "\nFast mode enabled")
      (princ "\nStandard mode enabled"))
  (+ x y)
)

(defun complex-func (a b c d)
  "A complex function with many arguments."
  (list a b c d)
)
