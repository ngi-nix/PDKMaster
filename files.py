#!/bin/env python3
"""Python code for parsing a Cadence technology file"""
# SPDX-License-Identifier: GPL-2.0-or-later OR AGPL-3.0-or-later OR CERN-OHL-S-2.0+
_pdkdir = "/home/verhaegs/eda/Chips4Makers/PDKs"

techfiles = (
    ("test.tf", "testtech.yaml"),
    (_pdkdir+"/TSMCPDK_tsmc035mm_3d3v_5v/techfile",
     "TSMC_CM035_TechFile.yaml"),
    (_pdkdir+"/TSMCPDK_C018RF_1P6M_4X1U_20KUTM_2fFMIM/techfile",
     "TSMC_CM018RF_TechFile.yaml"),
    (_pdkdir+"/SkyWaterPDK_s8/VirtuosoOA/techfiles/s8phirs_10r.tf",
     "SkyWater_s8phirs_10r_TechFile.yaml"),
    (_pdkdir+"/OnSemiPDK_amis350uc/lib/amis350uc/physical/dfii/amis350ucakxx/Rev3.13/techfile.tf",
     "OnSemi_amis350uc_TechFile.yaml"),
    (_pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_H35/TECH_H35B4/techfile4.asc",
     "AMS_H35B4_TechFile.yaml"),
    (_pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_H35/TECH_H35B4_VHV/techfile4.asc",
     "AMS_H35B4_VHV_TechFile.yaml"),
    (_pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_H35/TECH_H35B4_THINMET4/techfile4.asc",
     "AMS_H35B4_THINMET4_TechFile.yaml"),
    (_pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_S35/TECH_S35D4/techfile4.asc",
     "AMS_S35D4_TechFile.yaml"),
    (_pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_C35/TECH_C35B4/techfile4.asc",
     "AMS_C35B4_TechFile.yaml"),
    (_pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_C35/TECH_C35B4_THICKMET4/techfile4.asc",
     "AMS_C35B4_THICKMET4_TechFile.yaml"),
)

assurafiles = (
    (_pdkdir+"/TSMCPDK_tsmc035mm_3d3v_5v/Techfile/Assura/drc/2p3m/UM35P_5V_3M.24a",
     "TSMC_CM035_2P3M_DRC.yaml"),
    (_pdkdir+"/TSMCPDK_tsmc035mm_3d3v_5v/Techfile/Assura/drc/2p3m/UM35P_5V_3M.ANT.24a",
     "TSMC_CM035_2P3M_Antenna.yaml"),
    (_pdkdir+"/TSMCPDK_tsmc035mm_3d3v_5v/Techfile/Assura/lvsrcx/2p3m/extract.rul",
     "TSMC_CM035_2P3M_Extract.yaml"),
    (_pdkdir+"/TSMCPDK_tsmc035mm_3d3v_5v/Techfile/Assura/lvsrcx/2p3m/compare.rul",
     "TSMC_CM035_2P3M_LVS.yaml"),
    (_pdkdir+"/TSMCPDK_tsmc035mm_3d3v_5v/Techfile/Assura/drc/2p4m/UM35P_5V_4M.24a",
     "TSMC_CM035_2P4M_DRC.yaml"),
    (_pdkdir+"/TSMCPDK_tsmc035mm_3d3v_5v/Techfile/Assura/drc/2p4m/UM35P_5V_4M.ANT.24a",
     "TSMC_CM035_2P4M_Antenna.yaml"),
    (_pdkdir+"/TSMCPDK_tsmc035mm_3d3v_5v/Techfile/Assura/lvsrcx/2p4m/extract.rul",
     "TSMC_CM035_2P4M_Extract.yaml"),
    (_pdkdir+"/TSMCPDK_tsmc035mm_3d3v_5v/Techfile/Assura/lvsrcx/2p4m/compare.rul",
     "TSMC_CM035_2P4M_LVS.yaml"),
    (_pdkdir+"/TSMCPDK_C018RF_1P6M_4X1U_20KUTM_2fFMIM/Assura/drc/assura.drc",
     "TSMC_CM018RF_DRC.yaml"),
    (_pdkdir+"/TSMCPDK_C018RF_1P6M_4X1U_20KUTM_2fFMIM/Assura/drc/ANTENNA/assura.ant",
     "TSMC_CM018RF_Antenna.yaml"),
    (_pdkdir+"/TSMCPDK_C018RF_1P6M_4X1U_20KUTM_2fFMIM/Assura/lvs_rcx/extract.rul",
     "TSMC_CM018RF_Extract.yaml"),
    (_pdkdir+"/TSMCPDK_C018RF_1P6M_4X1U_20KUTM_2fFMIM/Assura/lvs_rcx/compare.rul",
     "TSMC_CM018RF_LVS.yaml"),
    # No Assura files for SkyWater
    # No Assura files for OnSemi PDK
    (_pdkdir+"/AMSPDK_HK_C35H35S35/assura/c35b4/c35b4/drc.rul",
     "AMS_C35B4_DRC.yaml"),
    (_pdkdir+"/AMSPDK_HK_C35H35S35/assura/c35b4/c35b4/compare.rul",
     "AMS_C35B4_LVS.yaml"),
    (_pdkdir+"/AMSPDK_HK_C35H35S35/assura/c35b4/c35b4/extract.rul",
     "AMS_C35B4_Extract.yaml"),
    (_pdkdir+"/AMSPDK_HK_C35H35S35/assura/c35b4/c35b4/dfm.rul",
     "AMS_C35B4_DFM.yaml"),
    (_pdkdir+"/AMSPDK_HK_C35H35S35/assura/c35b4/c35b4/deviceInfo.rul",
     "AMS_C35B4_DevInfo.yaml"),
    (_pdkdir+"/AMSPDK_HK_C35H35S35/assura/c35b4/notchfill/notchfill.rul",
     "AMS_C35B4_NothFill.yaml"),
    (_pdkdir+"/AMSPDK_HK_C35H35S35/assura/c35b4/fillmettop/c35b4_fillmettop.rul",
     "AMS_C35B4_FillMetalTop.yaml"),
    (_pdkdir+"/AMSPDK_HK_C35H35S35/assura/h35b4/h35b4/drc.rul",
     "AMS_H35B4_DRC.yaml"),
    (_pdkdir+"/AMSPDK_HK_C35H35S35/assura/h35b4/h35b4/leak.rul",
     "AMS_H35B4_Leak_DRC.yaml"),
    (_pdkdir+"/AMSPDK_HK_C35H35S35/assura/h35b4/h35b4/leak2/leak.rul",
     "AMS_H35B4_Leak2_DRC.yaml"),
    (_pdkdir+"/AMSPDK_HK_C35H35S35/assura/h35b4/h35b4/compare.rul",
     "AMS_H35B4_LVS.yaml"),
    (_pdkdir+"/AMSPDK_HK_C35H35S35/assura/h35b4/h35b4/compare_hv.rul",
     "AMS_H35B4_HV_LVS.yaml"),
    (_pdkdir+"/AMSPDK_HK_C35H35S35/assura/h35b4/h35b4/extract.rul",
     "AMS_H35B4_Extract.yaml"),
    (_pdkdir+"/AMSPDK_HK_C35H35S35/assura/h35b4/h35b4/dfm.rul",
     "AMS_H35B4_DFM.yaml"),
    (_pdkdir+"/AMSPDK_HK_C35H35S35/assura/h35b4/h35b4/deviceInfo.rul",
     "AMS_H35B4_DevInfo.yaml"),
    (_pdkdir+"/AMSPDK_HK_C35H35S35/assura/h35b4/notchfill/notchfill.rul",
     "AMS_H35B4_NothFill.yaml"),
    (_pdkdir+"/AMSPDK_HK_C35H35S35/assura/h35b4/fillmettop/h35b4_fillmettop.rul",
     "AMS_H35B4_FillMetalTop.yaml"),
    (_pdkdir+"/AMSPDK_HK_C35H35S35/assura/s35d4/s35d4/drc.rul",
     "AMS_S35D4_DRC.yaml"),
    (_pdkdir+"/AMSPDK_HK_C35H35S35/assura/s35d4/s35d4/compare.rul",
     "AMS_S35D4_LVS.yaml"),
    (_pdkdir+"/AMSPDK_HK_C35H35S35/assura/s35d4/s35d4/compare_bip.rul",
     "AMS_S35D4_Bipolar_LVS.yaml"),
    (_pdkdir+"/AMSPDK_HK_C35H35S35/assura/s35d4/s35d4/extract.rul",
     "AMS_S35D4_Extract.yaml"),
    (_pdkdir+"/AMSPDK_HK_C35H35S35/assura/s35d4/s35d4/dfm.rul",
     "AMS_S35D4_DFM.yaml"),
    (_pdkdir+"/AMSPDK_HK_C35H35S35/assura/s35d4/s35d4/deviceInfo.rul",
     "AMS_S35D4_DevInfo.yaml"),
    (_pdkdir+"/AMSPDK_HK_C35H35S35/assura/s35d4/notchfill/notchfill.rul",
     "AMS_S35D4_NothFill.yaml"),
    (_pdkdir+"/AMSPDK_HK_C35H35S35/assura/s35d4/fillmettop/s35d4_fillmettop.rul",
     "AMS_S35D4_FillMetalTop.yaml"),
# TODO:

# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4m6/extract.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4m6/bind.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4m6/drc.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4m6/compare.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4m6/dfm.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4m6/deviceInfo.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4all/dfm.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4thinall/extract.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4thinall/bind.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4thinall/drc.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4thinall/compare.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4thinall/dfm.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4thinall/deviceInfo.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4o0/dfm.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4o1/extract.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4o1/bind.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4o1/drc.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4o1/compare.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4o1/dfm.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4o1/deviceInfo.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4thickall/extract.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4thickall/bind.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4thickall/drc.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4thickall/compare.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4thickall/dfm.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4thickall/deviceInfo.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4m3/extract.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4m3/bind.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4m3/drc.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4m3/compare.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4m3/dfm.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4m3/deviceInfo.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4t1/extract.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4t1/bind.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4t1/drc.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4t1/compare.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4t1/dfm.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4t1/deviceInfo.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4c3/extract.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4c3/bind.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4c3/drc.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4c3/compare.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4c3/dfm.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4c3/deviceInfo.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4c0/extract.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4c0/bind.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4c0/drc.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4c0/compare.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4c0/dfm.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4c0/deviceInfo.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4_thick/notchfill/notchfill.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4_thick/fillmettop/c35b4_thick_fillmettop.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4_thick/extract.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4_thick/bind.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4_thick/compare.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4_thick/drc.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4_thick/dfm.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4_thick/fillpattern/c35b4_thick_fillpattern.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4_thick/deviceInfo.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/fillpattern/c35b4_fillpattern.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4oa/dfm.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4z1/extract.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4z1/bind.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4z1/drc.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4z1/compare.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4z1/dfm.rul
# ./AMSPDK_HK_C35H35S35/assura/c35b4/c35b4z1/deviceInfo.rul

# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4d3/compare_hv.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4d3/extract.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4d3/bind.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4d3/leak.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4d3/drc.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4d3/compare.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4d3/dfm.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4d3/deviceInfo.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4/bind.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4/leak2/text.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4_thin/notchfill/notchfill.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4_thin/compare_hv.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4_thin/fillmettop/h35b4_thin_fillmettop.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4_thin/extract.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4_thin/bind.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4_thin/leak.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4_thin/drc.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4_thin/compare.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4_thin/dfm.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4_thin/deviceInfo.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4s1/compare_hv.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4s1/extract.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4s1/bind.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4s1/leak.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4s1/drc.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4s1/compare.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4s1/dfm.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4s1/deviceInfo.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4_thin_mim5v/extract.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4_thin_mim5v/dfm.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4jd/compare_hv.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4jd/extract.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4jd/bind.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4jd/leak.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4jd/drc.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4jd/compare.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4jd/dfm.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4jd/deviceInfo.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4v1/compare_hv.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4v1/extract.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4v1/bind.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4v1/leak.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4v1/drc.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4v1/compare.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4v1/dfm.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4v1/deviceInfo.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4vhvall/compare_hv.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4vhvall/extract.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4vhvall/bind.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4vhvall/leak.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4vhvall/drc.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4vhvall/compare.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4vhvall/dfm.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4vhvall/deviceInfo.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4kc/compare_hv.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4kc/extract.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4kc/bind.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4kc/leak.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4kc/drc.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4kc/compare.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4kc/dfm.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4kc/deviceInfo.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4thickall/compare_hv.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4thickall/extract.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4thickall/bind.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4thickall/leak.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4thickall/drc.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4thickall/compare.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4thickall/dfm.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4thickall/deviceInfo.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4l3/compare_hv.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4l3/extract.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4l3/bind.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4l3/leak.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4l3/drc.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4l3/compare.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4l3/dfm.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4l3/deviceInfo.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4s2/compare_hv.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4s2/extract.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4s2/bind.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4s2/leak.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4s2/drc.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4s2/compare.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4s2/dfm.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4s2/deviceInfo.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/fillpattern/h35b4_fillpattern.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4ld/compare_hv.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4ld/extract.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4ld/bind.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4ld/leak.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4ld/drc.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4ld/compare.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4ld/dfm.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4ld/deviceInfo.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4_vhv/compare_hv.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4_vhv/extract.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4_vhv/bind.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4_vhv/drc.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4_vhv/compare.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4_vhv/dfm.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4_vhv/deviceInfo.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4s5/compare_hv.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4s5/extract.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4s5/bind.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4s5/leak.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4s5/drc.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4s5/compare.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4s5/dfm.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4s5/deviceInfo.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4thinall/compare_hv.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4thinall/extract.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4thinall/bind.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4thinall/leak.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4thinall/drc.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4thinall/compare.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4thinall/dfm.rul
# ./AMSPDK_HK_C35H35S35/assura/h35b4/h35b4thinall/deviceInfo.rul

# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4h2/compare_bip.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4h2/extract.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4h2/bind.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4h2/drc.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4h2/compare.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4h2/dfm.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4h2/deviceInfo.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4/bind.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4hp/compare_bip.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4hp/extract.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4hp/bind.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4hp/drc.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4hp/compare.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4hp/dfm.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4hp/deviceInfo.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4m5/compare_bip.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4m5/extract.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4m5/bind.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4m5/drc.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4m5/compare.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4m5/dfm.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4m5/deviceInfo.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4h5/compare_bip.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4h5/extract.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4h5/bind.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4h5/drc.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4h5/compare.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4h5/dfm.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4h5/deviceInfo.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4all/compare_bip.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4all/extract.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4all/bind.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4all/drc.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4all/compare.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4all/dfm.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4all/deviceInfo.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4m6/dfm.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4m7/compare_bip.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4m7/extract.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4m7/bind.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4m7/drc.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4m7/compare.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4m7/dfm.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4m7/deviceInfo.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/fillpattern/s35d4_fillpattern.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4m2/compare_bip.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4m2/extract.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4m2/bind.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4m2/drc.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4m2/compare.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4m2/dfm.rul
# ./AMSPDK_HK_C35H35S35/assura/s35d4/s35d4m2/deviceInfo.rul

# ./AMSPDK_HK_C35H35S35/cds/HK_H35/TECH_H35B4_THINMET4/icc.data/icc_device.rul
# ./AMSPDK_HK_C35H35S35/cds/HK_H35/TECH_H35B4_THINMET4/icc.data/icc_block.rul
# ./AMSPDK_HK_C35H35S35/cds/HK_H35/TECH_H35B4_VHV/icc.data/icc_device.rul
# ./AMSPDK_HK_C35H35S35/cds/HK_H35/TECH_H35B4_VHV/icc.data/icc_block.rul
# ./AMSPDK_HK_C35H35S35/cds/HK_H35/TECH_H35B3/icc.data/icc_device.rul
# ./AMSPDK_HK_C35H35S35/cds/HK_H35/TECH_H35B3/icc.data/icc_block.rul
# ./AMSPDK_HK_C35H35S35/cds/HK_H35/TECH_H35B4/icc.data/icc_device.rul
# ./AMSPDK_HK_C35H35S35/cds/HK_H35/TECH_H35B4/icc.data/icc_block.rul
# ./AMSPDK_HK_C35H35S35/cds/HK_ALL/LEADFRAMES/bonding_dv.rul
# ./AMSPDK_HK_C35H35S35/cds/HK_ALL/LEADFRAMES/bonding.rul
# ./AMSPDK_HK_C35H35S35/cds/HK_ALL/LEADFRAMES/bonding_pinpad.rul
# ./AMSPDK_HK_C35H35S35/cds/HK_S35/TECH_S35D4/icc.data/icc_device.rul
# ./AMSPDK_HK_C35H35S35/cds/HK_S35/TECH_S35D4/icc.data/icc_block.rul
# ./AMSPDK_HK_C35H35S35/cds/HK_S35/TECH_S35D3/icc.data/icc_device.rul
# ./AMSPDK_HK_C35H35S35/cds/HK_S35/TECH_S35D3/icc.data/icc_block.rul
# ./AMSPDK_HK_C35H35S35/cds/HK_C35/TECH_C35B4/icc.data/icc_device.rul
# ./AMSPDK_HK_C35H35S35/cds/HK_C35/TECH_C35B4/icc.data/icc_block.rul
# ./AMSPDK_HK_C35H35S35/cds/HK_C35/TECH_C35B3/icc.data/icc_device.rul
# ./AMSPDK_HK_C35H35S35/cds/HK_C35/TECH_C35B3/icc.data/icc_block.rul

# ./AMSPDK_HK_C35H35S35/pvs/c35b4/c35b4m6/extview.rul
# ./AMSPDK_HK_C35H35S35/pvs/c35b4/c35b4thinall/extview.rul
# ./AMSPDK_HK_C35H35S35/pvs/c35b4/c35b4o1/extview.rul
# ./AMSPDK_HK_C35H35S35/pvs/c35b4/c35b4m3/extview.rul
# ./AMSPDK_HK_C35H35S35/pvs/c35b4/c35b4t1/extview.rul
# ./AMSPDK_HK_C35H35S35/pvs/c35b4/c35b4c3/extview.rul
# ./AMSPDK_HK_C35H35S35/pvs/c35b4/c35b4c0/extview.rul
# ./AMSPDK_HK_C35H35S35/pvs/c35b4/c35b4_thick/extview.rul
# ./AMSPDK_HK_C35H35S35/pvs/c35b4/c35b4oa/extview.rul
# ./AMSPDK_HK_C35H35S35/pvs/c35b4/c35b4/extview.rul
# ./AMSPDK_HK_C35H35S35/pvs/c35b4/c35b4z1/extview.rul
)

ilfiles = (
    _pdkdir+"/SkyWaterPDK_s8/MODELS/SPECTRE/skill/modelguiconfig.il",
    _pdkdir+"/SkyWaterPDK_s8/MODELS/SPECTRE/skill/skywater_menu.il",
    _pdkdir+"/SkyWaterPDK_s8/MODELS/SPECTRE/skill/modelgui.il",
    _pdkdir+"/SkyWaterPDK_s8/VirtuosoOA/SKILL/001-59001/s8/s8phirs-10r/info/devices.il",
    _pdkdir+"/SkyWaterPDK_s8/VirtuosoOA/SKILL/config/tech/info/devices.il",
    _pdkdir+"/SkyWaterPDK_s8/VirtuosoOA/SKILL/config/pcios/s8/s8phirs-10r/info/devices.il",
    _pdkdir+"/SkyWaterPDK_s8/VirtuosoOA/SKILL/config/pcios/s8/s8phirs-10r/info/edr.il",
    _pdkdir+"/SkyWaterPDK_s8/VirtuosoOA/SKILL/SkyWater.il",
    _pdkdir+"/SkyWaterPDK_s8/VirtuosoOA/libs/technology_library/libInit.il",
    _pdkdir+"/SkyWaterPDK_s8/VirtuosoOA/libs/tech/libInit.il",
    _pdkdir+"/SkyWaterPDK_s8/VirtuosoOA/libs/s8phirs_10r/libInit.il",
    _pdkdir+"/TSMCPDK_tsmc035mm_3d3v_5v/tsmc35mm/libInit.il",
    _pdkdir+"/TSMCPDK_C018RF_1P6M_4X1U_20KUTM_2fFMIM/tsmc18/libInit.il",
    _pdkdir+"/OnSemiPDK_amis350uc/lib/amis350uc/physical/dfii/amis350ucakxx/Rev3.13/libInit.il",
    _pdkdir+"/OnSemiPDK_amis350uc/lib/amis350uc/physical/dfii/amis350ucatxx/Rev5.3/libInit.il",
    _pdkdir+"/OnSemiPDK_amis350uc/lib/amis350uc/physical/dfii/amis350ucatxx/Rev5.3/AmisDeviceChecks.il",
    _pdkdir+"/OnSemiPDK_amis350uc/lib/tech/dklibs/tech_indep/eda/sheet/none/dfii/onSheetLib/Rev5.8/libInit.il",
    _pdkdir+"/OnSemiPDK_amis350uc/lib/tech/dklibs/tech_indep/eda/sheet/none/dfii/onSheetLib/Rev5.8/titleBlock.il",
    _pdkdir+"/OnSemiPDK_amis350uc/lib/tech/dklibs/tech_indep/eda/sheet/none/dfii/onSheetLib/Rev5.8/schConfig.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/spectre/s35/modelMap.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/spectre/s35/soac/modelMap.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/spectre/h35/modelMap.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/spectre/h35/soac/modelMap.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/spectre/c35/modelMap.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/spectre/c35/soac/modelMap.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/spectre/c35/soac/.deviceMap.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/spectre/c35/.deviceMap.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_H35/skill/ams_sdl.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_H35/skill/processes_h35b3.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_H35/skill/tips_h35b4.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_H35/skill/processes_h35b4.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_H35/skill/AMS_deviceAreaTable.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_H35/skill/tips_h35b3.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_H35/PRIMLIB/libInit.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_ALL/skill/ansCdlCompPrim.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_ALL/skill/ams_env.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_ALL/skill/ams_callBacks.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_ALL/skill/ams_customParametersAsSpectre.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_ALL/BORDERS/libInit.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_ALL/BORDERS/borders.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_S35/skill/ams_sdl.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_S35/skill/processes_internal_s35d4.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_S35/skill/processes_s35d3.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_S35/skill/tips_s35d4.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_S35/skill/processes_s35d4.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_S35/skill/processes_internal_s35d3.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_S35/skill/AMS_deviceAreaTable.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_S35/skill/tips_s35d3.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_S35/PRIMLIB/libInit.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_C35/skill/ams_sdl.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_C35/skill/processes_c35b3.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_C35/skill/tips_c35b4.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_C35/skill/tips_c35b3.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_C35/skill/processes_internal_c35b4.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_C35/skill/processes_c35b4.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_C35/skill/AMS_deviceAreaTable.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_C35/skill/processes_internal_c35b3.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_C35/skill/processes_c35a3.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_C35/PRIMLIB/libInit.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/hspiceS/s35/ams_hspiceS.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/hspiceS/h35/ams_hspiceS.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/hspiceS/h35/soac/ams_hspiceS.il",
    _pdkdir+"/AMSPDK_HK_C35H35S35/hspiceS/c35/ams_hspiceS.il", 
)

displayfiles = (
    (_pdkdir+"/SkyWaterPDK_s8/VirtuosoOA/libs/display.drf",
    "SkyWater_s8_Display.yaml"),
    (_pdkdir+"/TSMCPDK_tsmc035mm_3d3v_5v/display.drf",
    "TSMC_CM035_Display.yaml"),
    (_pdkdir+"/TSMCPDK_C018RF_1P6M_4X1U_20KUTM_2fFMIM/display.drf",
    "TSMC_CM018RF_Display.yaml"),
    (_pdkdir+"/OnSemiPDK_amis350uc/lib/amis350uc/physical/dfii/amis350ucakxx/Rev3.13/display.drf",
    "OnSemi_amis350uc_Display.yaml"),
    (_pdkdir+"/AMSPDK_HK_C35H35S35/cds/HK_ALL/env/display.drf",
    "AMS_HK_ALL_Display.yaml"),
)
