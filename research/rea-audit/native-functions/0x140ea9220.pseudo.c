
/* WARNING: Function: __security_check_cookie replaced with injection: security_check_cookie */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_140ea9220(longlong *param_1,longlong param_2,undefined8 param_3)

{
  int *piVar1;
  int iVar2;
  undefined4 uVar3;
  undefined8 uVar4;
  undefined8 uVar5;
  longlong *plVar6;
  longlong lVar7;
  longlong lVar8;
  undefined1 auStack_108 [32];
  undefined8 *puStack_e8;
  undefined8 uStack_d8;
  longlong *plStack_d0;
  longlong *plStack_c8;
  undefined8 uStack_c0;
  undefined4 uStack_b8;
  undefined8 uStack_b0;
  longlong *plStack_a8;
  longlong *plStack_a0;
  longlong *plStack_98;
  longlong alStack_88 [4];
  longlong lStack_68;
  undefined4 uStack_60;
  undefined4 uStack_5c;
  undefined4 uStack_58;
  undefined4 uStack_54;
  longlong lStack_48;
  undefined4 uStack_40;
  ulonglong uStack_38;
  
  uStack_38 = _DAT_1448c9b00 ^ (ulonglong)auStack_108;
  uStack_d8 = 0;
  (**(code **)(*param_1 + 0x160))();
  if ((*(int *)(*(longlong *)((longlong)ThreadLocalStoragePointer + (ulonglong)__tls_index * 8) +
               0x108) < _DAT_1448f30f0) && (FUN_1436d2ef4(&DAT_1448f30f0), _DAT_1448f30f0 == -1)) {
    FUN_140fe7ba0(&DAT_1448f30e8,L"OnlineSubsystem",1);
    FUN_1436d2e88(&DAT_1448f30f0);
  }
  uVar4 = _DAT_1448f30e8;
  uVar5 = thunk_FUN_140fcffd0();
  plVar6 = (longlong *)FUN_140fcff10(uVar5,uVar4);
  lVar7 = (**(code **)(*plVar6 + 0x50))(plVar6,uStack_d8);
  if ((lVar7 != 0) && (plVar6 = (longlong *)FUN_140d4d090(1), plVar6 != (longlong *)0x0)) {
    (**(code **)(*plVar6 + 0xe8))(plVar6,&plStack_d0);
    if ((plStack_d0 != (longlong *)0x0) && (lVar7 = *(longlong *)(param_2 + 0x298), lVar7 != 0)) {
      lVar8 = FUN_142e07be0();
      if ((*(int *)(lVar8 + 0x38) <= *(int *)(*(longlong *)(lVar7 + 0x10) + 0x38)) &&
         (*(longlong *)
           (*(longlong *)(*(longlong *)(lVar7 + 0x10) + 0x30) + (longlong)*(int *)(lVar8 + 0x38) * 8
           ) == lVar8 + 0x30)) {
        uVar3 = *(undefined4 *)(lVar7 + 0xb8);
        (**(code **)(*plVar6 + 0x80))(plVar6,&plStack_a0);
        if (plStack_a0 != (longlong *)0x0) {
          (**(code **)(*plStack_a0 + 0xf0))(plStack_a0,&uStack_b0,uVar3);
          puStack_e8 = &uStack_c0;
          uStack_c0 = 0;
          uStack_b8 = 0;
          alStack_88[0] = 0;
          alStack_88[1] = 0;
          lStack_68 = 0;
          uStack_60 = 0;
          uStack_5c = 0x80;
          uStack_58 = 0xffffffff;
          uStack_54 = 0;
          lStack_48 = 0;
          uStack_40 = 0;
          (**(code **)(*plStack_d0 + 8))(plStack_d0,uStack_b0,param_3,alStack_88);
          uStack_40 = 0;
          if (lStack_48 != 0) {
            FUN_140ef49c0();
          }
          FUN_140d4c140(alStack_88,0);
          if (lStack_68 != 0) {
            FUN_140ef49c0();
          }
          if (alStack_88[0] != 0) {
            FUN_140ef49c0();
          }
          if (plStack_a8 != (longlong *)0x0) {
            plVar6 = plStack_a8 + 1;
            *(int *)plVar6 = (int)*plVar6 + -1;
            if ((int)*plVar6 == 0) {
              (**(code **)*plStack_a8)(plStack_a8);
              piVar1 = (int *)((longlong)plStack_a8 + 0xc);
              *piVar1 = *piVar1 + -1;
              if (*piVar1 == 0) {
                (**(code **)(*plStack_a8 + 8))(plStack_a8,1);
              }
            }
          }
        }
        if (plStack_98 != (longlong *)0x0) {
          LOCK();
          plVar6 = plStack_98 + 1;
          lVar7 = *plVar6;
          *(int *)plVar6 = (int)*plVar6 + -1;
          UNLOCK();
          if ((int)lVar7 == 1) {
            (**(code **)*plStack_98)(plStack_98);
            LOCK();
            piVar1 = (int *)((longlong)plStack_98 + 0xc);
            iVar2 = *piVar1;
            *piVar1 = *piVar1 + -1;
            UNLOCK();
            if (iVar2 == 1) {
              (**(code **)(*plStack_98 + 8))(plStack_98,1);
            }
          }
        }
      }
    }
    if (plStack_c8 != (longlong *)0x0) {
      LOCK();
      plVar6 = plStack_c8 + 1;
      lVar7 = *plVar6;
      *(int *)plVar6 = (int)*plVar6 + -1;
      UNLOCK();
      if ((int)lVar7 == 1) {
        (**(code **)*plStack_c8)(plStack_c8);
        LOCK();
        piVar1 = (int *)((longlong)plStack_c8 + 0xc);
        iVar2 = *piVar1;
        *piVar1 = *piVar1 + -1;
        UNLOCK();
        if (iVar2 == 1) {
          (**(code **)(*plStack_c8 + 8))(plStack_c8,1);
        }
      }
    }
  }
  return;
}

