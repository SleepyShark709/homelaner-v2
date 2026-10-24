
/* WARNING: Function: __security_check_cookie replaced with injection: security_check_cookie */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined8 FUN_140ea7680(byte *param_1,undefined8 param_2)

{
  byte bVar1;
  int iVar2;
  undefined1 *puVar3;
  byte *pbVar4;
  undefined8 uVar5;
  undefined1 auStack_168 [32];
  undefined2 uStack_148;
  undefined1 uStack_138;
  undefined1 uStack_137;
  undefined1 uStack_136;
  undefined1 uStack_135;
  undefined1 auStack_134 [4];
  longlong lStack_130;
  undefined8 uStack_128;
  longlong lStack_120;
  undefined8 uStack_118;
  longlong lStack_110;
  undefined8 uStack_108;
  longlong lStack_100;
  undefined8 uStack_f8;
  longlong lStack_f0;
  undefined8 uStack_e8;
  undefined1 **ppuStack_d8;
  ulonglong *puStack_d0;
  longlong lStack_c8;
  int iStack_c0;
  longlong lStack_a8;
  int iStack_94;
  undefined1 auStack_90 [8];
  undefined1 *puStack_88;
  int iStack_80;
  undefined1 *puStack_78;
  longlong *plStack_70;
  undefined1 *puStack_68;
  longlong *plStack_60;
  undefined1 *puStack_58;
  longlong *plStack_50;
  undefined1 *puStack_48;
  longlong *plStack_40;
  undefined1 *puStack_38;
  longlong *plStack_30;
  ulonglong auStack_28 [2];
  
  auStack_28[0] = _DAT_1448c9b00 ^ (ulonglong)auStack_168;
  uStack_138 = 0;
  lStack_f0 = 0;
  uStack_e8 = 0;
  FUN_1407d7c80(&lStack_f0,0x14);
  iVar2 = (int)uStack_e8 + 0x14;
  uStack_e8 = CONCAT44(uStack_e8._4_4_,iVar2);
  if (uStack_e8._4_4_ < iVar2) {
    FUN_1407d7780(&lStack_f0);
  }
  uStack_148 = 0x3f;
  FUN_1407da340(lStack_f0,0x14,"UNDEFEATED_SubTask1");
  puStack_78 = &uStack_138;
  uStack_137 = 1;
  plStack_70 = &lStack_f0;
  lStack_100 = 0;
  uStack_f8 = 0;
  FUN_1407d7c80(&lStack_100,0x14);
  iVar2 = (int)uStack_f8 + 0x14;
  uStack_f8 = CONCAT44(uStack_f8._4_4_,iVar2);
  if (uStack_f8._4_4_ < iVar2) {
    FUN_1407d7780(&lStack_100);
  }
  uStack_148 = 0x3f;
  FUN_1407da340(lStack_100,0x14,"UNDEFEATED_SubTask2");
  puStack_68 = &uStack_137;
  uStack_136 = 2;
  plStack_60 = &lStack_100;
  lStack_110 = 0;
  uStack_108 = 0;
  FUN_1407d7c80(&lStack_110,0x14);
  iVar2 = (int)uStack_108 + 0x14;
  uStack_108 = CONCAT44(uStack_108._4_4_,iVar2);
  if (uStack_108._4_4_ < iVar2) {
    FUN_1407d7780(&lStack_110);
  }
  uStack_148 = 0x3f;
  FUN_1407da340(lStack_110,0x14,"UNDEFEATED_SubTask3");
  puStack_58 = &uStack_136;
  uStack_135 = 3;
  plStack_50 = &lStack_110;
  lStack_120 = 0;
  uStack_118 = 0;
  FUN_1407d7c80(&lStack_120,0x14);
  iVar2 = (int)uStack_118 + 0x14;
  uStack_118 = CONCAT44(uStack_118._4_4_,iVar2);
  if (uStack_118._4_4_ < iVar2) {
    FUN_1407d7780(&lStack_120);
  }
  uStack_148 = 0x3f;
  FUN_1407da340(lStack_120,0x14,"UNDEFEATED_SubTask4");
  puStack_48 = &uStack_135;
  auStack_134[0] = 4;
  plStack_40 = &lStack_120;
  lStack_130 = 0;
  uStack_128 = 0;
  FUN_1407d7c80(&lStack_130,0x18);
  iVar2 = (int)uStack_128 + 0x18;
  uStack_128 = CONCAT44(uStack_128._4_4_,iVar2);
  if (uStack_128._4_4_ < iVar2) {
    FUN_1407d7780(&lStack_130);
  }
  uStack_148 = 0x3f;
  FUN_1407da340(lStack_130,0x18,"UNDEFEATED_MainActivity");
  puStack_38 = auStack_134;
  plStack_30 = &lStack_130;
  ppuStack_d8 = &puStack_78;
  puStack_d0 = auStack_28;
  FUN_140ea6ed0(&lStack_c8,&ppuStack_d8);
  if (lStack_130 != 0) {
    FUN_140ef49c0();
  }
  if (lStack_120 != 0) {
    FUN_140ef49c0();
  }
  if (lStack_110 != 0) {
    FUN_140ef49c0();
  }
  if (lStack_100 != 0) {
    FUN_140ef49c0();
  }
  if (lStack_f0 != 0) {
    FUN_140ef49c0();
  }
  bVar1 = *param_1;
  if (iStack_c0 != iStack_94) {
    puVar3 = auStack_90;
    if (puStack_88 != (undefined1 *)0x0) {
      puVar3 = puStack_88;
    }
    for (iVar2 = *(int *)(puVar3 + ((longlong)iStack_80 - 1U & (ulonglong)bVar1) * 4); iVar2 != -1;
        iVar2 = *(int *)((longlong)iVar2 * 0x20 + 0x18 + lStack_c8)) {
      if (*(byte *)((longlong)iVar2 * 0x20 + lStack_c8) == bVar1) {
        if (iVar2 != -1) {
          puVar3 = auStack_90;
          if (puStack_88 != (undefined1 *)0x0) {
            puVar3 = puStack_88;
          }
          iVar2 = *(int *)(puVar3 + ((longlong)iStack_80 - 1U & (ulonglong)bVar1) * 4);
          goto LAB_140ea79f1;
        }
        break;
      }
    }
  }
  uVar5 = 0;
  goto LAB_140ea7979;
  while (iVar2 = *(int *)(pbVar4 + 0x18), pbVar4 = (byte *)0x0, iVar2 != -1) {
LAB_140ea79f1:
    pbVar4 = (byte *)((longlong)iVar2 * 0x20 + lStack_c8);
    if (*pbVar4 == bVar1) break;
  }
  FUN_1407de680(param_2,pbVar4 + 8);
  uVar5 = 1;
LAB_140ea7979:
  iStack_80 = 0;
  if (puStack_88 != (undefined1 *)0x0) {
    FUN_140ef49c0(puStack_88);
  }
  FUN_140ea73f0(&lStack_c8,0);
  if (lStack_a8 != 0) {
    FUN_140ef49c0();
  }
  if (lStack_c8 != 0) {
    FUN_140ef49c0();
  }
  return uVar5;
}

