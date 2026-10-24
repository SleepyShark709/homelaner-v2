
/* WARNING: Function: __security_check_cookie replaced with injection: security_check_cookie */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_140ea7da0(longlong *param_1,undefined1 param_2)

{
  uint uVar1;
  longlong lVar2;
  longlong lVar3;
  ulonglong uVar4;
  longlong lVar5;
  int iVar6;
  ulonglong uVar7;
  uint *puVar8;
  undefined1 auStack_1b8 [32];
  undefined2 uStack_198;
  undefined1 uStack_188;
  undefined1 uStack_187;
  undefined1 uStack_186;
  undefined1 uStack_185;
  undefined1 auStack_184 [4];
  longlong lStack_180;
  undefined8 uStack_178;
  longlong lStack_170;
  undefined8 uStack_168;
  longlong lStack_160;
  undefined8 uStack_158;
  longlong lStack_150;
  undefined8 uStack_148;
  longlong lStack_140;
  undefined8 uStack_138;
  undefined8 uStack_128;
  uint *puStack_120;
  int iStack_118;
  int iStack_114;
  uint uStack_110;
  undefined4 uStack_10c;
  longlong *plStack_108;
  uint uStack_100;
  uint uStack_fc;
  uint *puStack_f8;
  uint uStack_f0;
  int iStack_ec;
  undefined8 uStack_e8;
  longlong *plStack_d8;
  undefined8 uStack_d0;
  uint *puStack_c8;
  undefined8 uStack_c0;
  undefined1 *puStack_b8;
  longlong *plStack_b0;
  undefined1 *puStack_a8;
  longlong *plStack_a0;
  undefined1 *puStack_98;
  longlong *plStack_90;
  longlong alStack_88 [2];
  uint auStack_78 [4];
  uint *puStack_68;
  int iStack_60;
  longlong lStack_48;
  undefined4 uStack_40;
  ulonglong uStack_38;
  
  if (param_1 == (longlong *)0x0) {
    return;
  }
  uStack_38 = _DAT_1448c9b00 ^ (ulonglong)auStack_1b8;
  lVar3 = (**(code **)(*param_1 + 0x160))();
  if (lVar3 == 0) {
    return;
  }
  lVar3 = *(longlong *)(lVar3 + 0x180);
  if (lVar3 == 0) {
    return;
  }
  uVar4 = FUN_140eaa020();
  uVar7 = 0;
  if ((uVar4 != 0) && (lVar5 = FUN_140eaa020(), lVar5 != 0)) {
    if ((*(int *)(lVar5 + 0x38) <= *(int *)(uVar4 + 0x38)) &&
       (*(longlong *)(*(longlong *)(uVar4 + 0x30) + (longlong)*(int *)(lVar5 + 0x38) * 8) ==
        lVar5 + 0x30)) goto LAB_140ea7e45;
  }
  uVar4 = uVar7;
LAB_140ea7e45:
  lVar3 = FUN_142c7c100(lVar3 + 0xe0,uVar4);
  if ((lVar3 != 0) && (lVar5 = FUN_1428c18a0(param_1,0), lVar5 != 0)) {
    uStack_188 = 0;
    lStack_140 = 0;
    uStack_138 = 0;
    FUN_1407d7c80(&lStack_140,0x14);
    iVar6 = (int)uStack_138 + 0x14;
    uStack_138 = CONCAT44(uStack_138._4_4_,iVar6);
    if (uStack_138._4_4_ < iVar6) {
      FUN_1407d7780(&lStack_140);
    }
    uStack_198 = 0x3f;
    FUN_1407da340(lStack_140,0x14,"UNDEFEATED_SubTask1");
    plStack_d8 = (longlong *)&uStack_188;
    uStack_187 = 1;
    uStack_d0 = &lStack_140;
    lStack_150 = 0;
    uStack_148 = 0;
    FUN_1407d7c80(&lStack_150,0x14);
    iVar6 = (int)uStack_148 + 0x14;
    uStack_148 = CONCAT44(uStack_148._4_4_,iVar6);
    if (uStack_148._4_4_ < iVar6) {
      FUN_1407d7780(&lStack_150);
    }
    uStack_198 = 0x3f;
    FUN_1407da340(lStack_150,0x14,"UNDEFEATED_SubTask2");
    puStack_c8 = (uint *)&uStack_187;
    uStack_186 = 2;
    uStack_c0 = &lStack_150;
    lStack_160 = 0;
    uStack_158 = 0;
    FUN_1407d7c80(&lStack_160,0x14);
    iVar6 = (int)uStack_158 + 0x14;
    uStack_158 = CONCAT44(uStack_158._4_4_,iVar6);
    if (uStack_158._4_4_ < iVar6) {
      FUN_1407d7780(&lStack_160);
    }
    uStack_198 = 0x3f;
    FUN_1407da340(lStack_160,0x14,"UNDEFEATED_SubTask3");
    puStack_b8 = &uStack_186;
    uStack_185 = 3;
    plStack_b0 = &lStack_160;
    lStack_170 = 0;
    uStack_168 = 0;
    FUN_1407d7c80(&lStack_170,0x14);
    iVar6 = (int)uStack_168 + 0x14;
    uStack_168 = CONCAT44(uStack_168._4_4_,iVar6);
    if (uStack_168._4_4_ < iVar6) {
      FUN_1407d7780(&lStack_170);
    }
    uStack_198 = 0x3f;
    FUN_1407da340(lStack_170,0x14,"UNDEFEATED_SubTask4");
    puStack_a8 = &uStack_185;
    auStack_184[0] = 4;
    plStack_a0 = &lStack_170;
    lStack_180 = 0;
    uStack_178 = 0;
    FUN_1407d7c80(&lStack_180,0x18);
    iVar6 = (int)uStack_178 + 0x18;
    uStack_178 = CONCAT44(uStack_178._4_4_,iVar6);
    if (uStack_178._4_4_ < iVar6) {
      FUN_1407d7780(&lStack_180);
    }
    uStack_198 = 0x3f;
    FUN_1407da340(lStack_180,0x18,"UNDEFEATED_MainActivity");
    puStack_98 = auStack_184;
    plStack_90 = &lStack_180;
    uStack_128 = &plStack_d8;
    puStack_120 = (uint *)alStack_88;
    FUN_140ea6ed0(alStack_88,&uStack_128);
    if (lStack_180 != 0) {
      FUN_140ef49c0();
    }
    if (lStack_170 != 0) {
      FUN_140ef49c0();
    }
    if (lStack_160 != 0) {
      FUN_140ef49c0();
    }
    if (lStack_150 != 0) {
      FUN_140ef49c0();
    }
    if (lStack_140 != 0) {
      FUN_140ef49c0();
    }
    puStack_120 = auStack_78;
    uStack_128._0_4_ = 0;
    uStack_128._4_4_ = 1;
    iStack_114 = 0;
    uStack_110 = 0;
    if (iStack_60 != 0) {
      puVar8 = auStack_78;
      if (puStack_68 != (uint *)0x0) {
        puVar8 = puStack_68;
      }
      uVar1 = *puVar8;
      uVar4 = uVar7;
      while (uVar1 == 0) {
        uStack_128._0_4_ = (int)uVar7 + 1;
        uVar7 = (ulonglong)(uint)uStack_128;
        uStack_110 = (int)uVar4 + 0x20;
        uVar4 = (ulonglong)uStack_110;
        if ((int)((iStack_60 + -1 >> 0x1f & 0x1fU) + iStack_60 + -1) >> 5 < (int)(uint)uStack_128) {
          iStack_114 = iStack_60;
          goto LAB_140ea8197;
        }
        uVar1 = puVar8[(int)(uint)uStack_128];
      }
      uStack_128._4_4_ = -uVar1 & uVar1;
      uVar7 = (ulonglong)uStack_128._4_4_ * 2 | 1;
      lVar2 = 0x3f;
      if (uVar7 != 0) {
        for (; uVar7 >> lVar2 == 0; lVar2 = lVar2 + -1) {
        }
      }
      iStack_114 = (int)lVar2 + -1 + uStack_110;
      if (iStack_60 < iStack_114) {
        iStack_114 = iStack_60;
      }
    }
LAB_140ea8197:
    uStack_f0 = 0xffffffff;
    iStack_ec = iStack_114;
    uStack_e8 = CONCAT44(uStack_10c,uStack_110);
    plStack_d8 = alStack_88;
    iStack_118 = -1 << ((byte)iStack_60 & 0x1f);
    uStack_d0._0_4_ = (uint)uStack_128;
    uStack_d0._4_4_ = uStack_128._4_4_;
    iStack_114 = iStack_60;
    uStack_100 = (uint)uStack_128;
    uStack_fc = uStack_128._4_4_;
    puStack_f8 = puStack_120;
    puStack_c8 = puStack_120;
    puStack_b8 = (undefined1 *)uStack_e8;
    uStack_c0._0_4_ = uStack_f0;
    uStack_c0._4_4_ = iStack_ec;
    plStack_108 = plStack_d8;
    while (((iStack_ec != iStack_60 || (puStack_f8 != auStack_78)) || (plStack_108 != alStack_88)))
    {
      FUN_140ea8fc0(lVar3,lVar5,*plStack_108 + (longlong)iStack_ec * 0x20 + 8,param_2);
      uStack_f0 = uStack_f0 & ~uStack_fc;
      FUN_1407ce440(&uStack_100);
    }
    uStack_40 = 0;
    if (lStack_48 != 0) {
      FUN_140ef49c0();
    }
    FUN_140ea73f0(alStack_88,0);
    if (puStack_68 != (uint *)0x0) {
      FUN_140ef49c0();
    }
    if (alStack_88[0] != 0) {
      FUN_140ef49c0();
    }
  }
  return;
}

