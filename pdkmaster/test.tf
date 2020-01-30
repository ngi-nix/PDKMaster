f(
; Single line comment
  ( bondpad_layer       "NOTUSED"       )
  ( text_layers         (("TEXT" "drawing")) )
  (-1)
  ()
  g()
  ; Quoted string
  (enclosingLayers "(((\\\"PPLUS\\\" \\\"drawing\\\") 0.25 ?coverInterior nil ?useEncLayer t ?pin nil))")
  techParams(							
    ( LEFDEF_OVERLAP_LAYER_NAME	"OVERLAP"       )		
  ) ;techParams*/
  /* Testing
     multiline comment */
  " "
  a[2]
  a || { c }
  " ; "
  (nil -0.2 -3) ; Should be list with three elements, not one expression
  (a-3) ; One expression in list
  midY = (cadadr(cv ~> bBox) + cadar(cv~>bBox)-1.6)/2 ; One expression inside ()
  if(dY < 3-2.3 then printf("OK")) ; One expression before then
)
