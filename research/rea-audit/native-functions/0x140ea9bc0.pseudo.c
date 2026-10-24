
void FUN_140ea9bc0(undefined8 param_1,longlong param_2,undefined1 *param_3)

{
  undefined1 uVar1;
  longlong *plVar2;
  undefined1 *puVar3;
  undefined1 auStackX_10 [8];
  longlong alStack_18 [2];
  
  auStackX_10[0] = 0;
  *(undefined8 *)(param_2 + 0x38) = 0;
  if (*(longlong *)(param_2 + 0x20) == 0) {
    *(undefined8 *)(param_2 + 0x80) = *(undefined8 *)(*(longlong *)(param_2 + 0x80) + 0x20);
    FUN_1411e6720(param_2,auStackX_10);
  }
  else {
    FUN_1411e66f0(param_2,*(undefined8 *)(param_2 + 0x18),auStackX_10);
  }
  alStack_18[0] = 0;
  alStack_18[1] = 0;
  puVar3 = auStackX_10;
  if (*(undefined1 **)(param_2 + 0x38) != (undefined1 *)0x0) {
    puVar3 = *(undefined1 **)(param_2 + 0x38);
  }
  *(undefined8 *)(param_2 + 0x38) = 0;
  if (*(longlong *)(param_2 + 0x20) == 0) {
    *(undefined8 *)(param_2 + 0x80) = *(undefined8 *)(*(longlong *)(param_2 + 0x80) + 0x20);
    FUN_1411e6720(param_2,alStack_18);
  }
  else {
    FUN_1411e66f0(param_2,*(undefined8 *)(param_2 + 0x18),alStack_18);
  }
  plVar2 = alStack_18;
  if (*(longlong **)(param_2 + 0x38) != (longlong *)0x0) {
    plVar2 = *(longlong **)(param_2 + 0x38);
  }
  *(ulonglong *)(param_2 + 0x20) =
       (ulonglong)(*(longlong *)(param_2 + 0x20) != 0) + *(longlong *)(param_2 + 0x20);
  uVar1 = FUN_140ea7680(puVar3,plVar2);
  *param_3 = uVar1;
  if (alStack_18[0] != 0) {
    FUN_140ef49c0();
  }
  return;
}

