
void FUN_140ea9b00(undefined8 param_1,longlong param_2)

{
  undefined1 auStackX_10 [16];
  undefined8 uStackX_20;
  
  uStackX_20 = 0;
  FUN_1411bee80();
  if (*(longlong *)(param_2 + 0x20) == 0) {
    *(undefined8 *)(param_2 + 0x80) = *(undefined8 *)(*(longlong *)(param_2 + 0x80) + 0x20);
    FUN_1411e6720(param_2,&uStackX_20);
  }
  else {
    FUN_1411e66f0(param_2,*(undefined8 *)(param_2 + 0x18),&uStackX_20);
  }
  auStackX_10[0] = 0;
  FUN_14117c350();
  if (*(longlong *)(param_2 + 0x20) == 0) {
    *(undefined8 *)(param_2 + 0x80) = *(undefined8 *)(*(longlong *)(param_2 + 0x80) + 0x20);
    FUN_1411e6720(param_2,auStackX_10);
  }
  else {
    FUN_1411e66f0(param_2,*(undefined8 *)(param_2 + 0x18),auStackX_10);
  }
  *(ulonglong *)(param_2 + 0x20) =
       (ulonglong)(*(longlong *)(param_2 + 0x20) != 0) + *(longlong *)(param_2 + 0x20);
  FUN_140ea7580(uStackX_20,auStackX_10[0]);
  return;
}

