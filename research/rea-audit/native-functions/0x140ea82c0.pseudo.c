
void FUN_140ea82c0(longlong *param_1,undefined1 param_2)

{
  char cVar1;
  longlong lVar2;
  longlong lVar3;
  longlong lVar4;
  undefined1 auStackX_10 [8];
  longlong alStack_18 [2];
  
  if (param_1 == (longlong *)0x0) {
    return;
  }
  auStackX_10[0] = param_2;
  lVar2 = (**(code **)(*param_1 + 0x160))();
  if (lVar2 == 0) {
    return;
  }
  lVar2 = *(longlong *)(lVar2 + 0x180);
  if (lVar2 == 0) {
    return;
  }
  lVar3 = FUN_140eaa020();
  if ((lVar3 != 0) && (lVar4 = FUN_140eaa020(), lVar4 != 0)) {
    if ((*(int *)(lVar4 + 0x38) <= *(int *)(lVar3 + 0x38)) &&
       (*(longlong *)(*(longlong *)(lVar3 + 0x30) + (longlong)*(int *)(lVar4 + 0x38) * 8) ==
        lVar4 + 0x30)) goto LAB_140ea8334;
  }
  lVar3 = 0;
LAB_140ea8334:
  lVar2 = FUN_142c7c100(lVar2 + 0xe0,lVar3);
  if ((lVar2 != 0) && (lVar3 = FUN_1428c18a0(param_1,0), lVar3 != 0)) {
    alStack_18[0] = 0;
    alStack_18[1] = 0;
    cVar1 = FUN_140ea7680(auStackX_10,alStack_18);
    if (cVar1 != '\0') {
      FUN_140ea9220(lVar2,lVar3,alStack_18);
    }
    if (alStack_18[0] != 0) {
      FUN_140ef49c0();
    }
  }
  return;
}

