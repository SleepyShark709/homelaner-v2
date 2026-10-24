
void FUN_140ea9cc0(undefined8 param_1,longlong param_2)

{
  int aiStackX_10 [4];
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
  aiStackX_10[0] = 0;
  FUN_1411be170();
  if (*(longlong *)(param_2 + 0x20) == 0) {
    *(undefined8 *)(param_2 + 0x80) = *(undefined8 *)(*(longlong *)(param_2 + 0x80) + 0x20);
    FUN_1411e6720(param_2,aiStackX_10);
  }
  else {
    FUN_1411e66f0(param_2,*(undefined8 *)(param_2 + 0x18),aiStackX_10);
  }
  *(ulonglong *)(param_2 + 0x20) =
       (ulonglong)(*(longlong *)(param_2 + 0x20) != 0) + *(longlong *)(param_2 + 0x20);
  FUN_140ea7da0(uStackX_20,aiStackX_10[0] != 0);
  return;
}

