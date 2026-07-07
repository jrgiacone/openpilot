#include "pose.h"

namespace {
#define DIM 18
#define EDIM 18
#define MEDIM 18
typedef void (*Hfun)(double *, double *, double *);
const static double MAHA_THRESH_4 = 7.814727903251177;
const static double MAHA_THRESH_10 = 7.814727903251177;
const static double MAHA_THRESH_13 = 7.814727903251177;
const static double MAHA_THRESH_14 = 7.814727903251177;

/******************************************************************************
 *                      Code generated with SymPy 1.14.0                      *
 *                                                                            *
 *              See http://www.sympy.org/ for more information.               *
 *                                                                            *
 *                         This file is part of 'ekf'                         *
 ******************************************************************************/
void err_fun(double *nom_x, double *delta_x, double *out_3654460514432875415) {
   out_3654460514432875415[0] = delta_x[0] + nom_x[0];
   out_3654460514432875415[1] = delta_x[1] + nom_x[1];
   out_3654460514432875415[2] = delta_x[2] + nom_x[2];
   out_3654460514432875415[3] = delta_x[3] + nom_x[3];
   out_3654460514432875415[4] = delta_x[4] + nom_x[4];
   out_3654460514432875415[5] = delta_x[5] + nom_x[5];
   out_3654460514432875415[6] = delta_x[6] + nom_x[6];
   out_3654460514432875415[7] = delta_x[7] + nom_x[7];
   out_3654460514432875415[8] = delta_x[8] + nom_x[8];
   out_3654460514432875415[9] = delta_x[9] + nom_x[9];
   out_3654460514432875415[10] = delta_x[10] + nom_x[10];
   out_3654460514432875415[11] = delta_x[11] + nom_x[11];
   out_3654460514432875415[12] = delta_x[12] + nom_x[12];
   out_3654460514432875415[13] = delta_x[13] + nom_x[13];
   out_3654460514432875415[14] = delta_x[14] + nom_x[14];
   out_3654460514432875415[15] = delta_x[15] + nom_x[15];
   out_3654460514432875415[16] = delta_x[16] + nom_x[16];
   out_3654460514432875415[17] = delta_x[17] + nom_x[17];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_5462197318257341854) {
   out_5462197318257341854[0] = -nom_x[0] + true_x[0];
   out_5462197318257341854[1] = -nom_x[1] + true_x[1];
   out_5462197318257341854[2] = -nom_x[2] + true_x[2];
   out_5462197318257341854[3] = -nom_x[3] + true_x[3];
   out_5462197318257341854[4] = -nom_x[4] + true_x[4];
   out_5462197318257341854[5] = -nom_x[5] + true_x[5];
   out_5462197318257341854[6] = -nom_x[6] + true_x[6];
   out_5462197318257341854[7] = -nom_x[7] + true_x[7];
   out_5462197318257341854[8] = -nom_x[8] + true_x[8];
   out_5462197318257341854[9] = -nom_x[9] + true_x[9];
   out_5462197318257341854[10] = -nom_x[10] + true_x[10];
   out_5462197318257341854[11] = -nom_x[11] + true_x[11];
   out_5462197318257341854[12] = -nom_x[12] + true_x[12];
   out_5462197318257341854[13] = -nom_x[13] + true_x[13];
   out_5462197318257341854[14] = -nom_x[14] + true_x[14];
   out_5462197318257341854[15] = -nom_x[15] + true_x[15];
   out_5462197318257341854[16] = -nom_x[16] + true_x[16];
   out_5462197318257341854[17] = -nom_x[17] + true_x[17];
}
void H_mod_fun(double *state, double *out_3413546436148806037) {
   out_3413546436148806037[0] = 1.0;
   out_3413546436148806037[1] = 0.0;
   out_3413546436148806037[2] = 0.0;
   out_3413546436148806037[3] = 0.0;
   out_3413546436148806037[4] = 0.0;
   out_3413546436148806037[5] = 0.0;
   out_3413546436148806037[6] = 0.0;
   out_3413546436148806037[7] = 0.0;
   out_3413546436148806037[8] = 0.0;
   out_3413546436148806037[9] = 0.0;
   out_3413546436148806037[10] = 0.0;
   out_3413546436148806037[11] = 0.0;
   out_3413546436148806037[12] = 0.0;
   out_3413546436148806037[13] = 0.0;
   out_3413546436148806037[14] = 0.0;
   out_3413546436148806037[15] = 0.0;
   out_3413546436148806037[16] = 0.0;
   out_3413546436148806037[17] = 0.0;
   out_3413546436148806037[18] = 0.0;
   out_3413546436148806037[19] = 1.0;
   out_3413546436148806037[20] = 0.0;
   out_3413546436148806037[21] = 0.0;
   out_3413546436148806037[22] = 0.0;
   out_3413546436148806037[23] = 0.0;
   out_3413546436148806037[24] = 0.0;
   out_3413546436148806037[25] = 0.0;
   out_3413546436148806037[26] = 0.0;
   out_3413546436148806037[27] = 0.0;
   out_3413546436148806037[28] = 0.0;
   out_3413546436148806037[29] = 0.0;
   out_3413546436148806037[30] = 0.0;
   out_3413546436148806037[31] = 0.0;
   out_3413546436148806037[32] = 0.0;
   out_3413546436148806037[33] = 0.0;
   out_3413546436148806037[34] = 0.0;
   out_3413546436148806037[35] = 0.0;
   out_3413546436148806037[36] = 0.0;
   out_3413546436148806037[37] = 0.0;
   out_3413546436148806037[38] = 1.0;
   out_3413546436148806037[39] = 0.0;
   out_3413546436148806037[40] = 0.0;
   out_3413546436148806037[41] = 0.0;
   out_3413546436148806037[42] = 0.0;
   out_3413546436148806037[43] = 0.0;
   out_3413546436148806037[44] = 0.0;
   out_3413546436148806037[45] = 0.0;
   out_3413546436148806037[46] = 0.0;
   out_3413546436148806037[47] = 0.0;
   out_3413546436148806037[48] = 0.0;
   out_3413546436148806037[49] = 0.0;
   out_3413546436148806037[50] = 0.0;
   out_3413546436148806037[51] = 0.0;
   out_3413546436148806037[52] = 0.0;
   out_3413546436148806037[53] = 0.0;
   out_3413546436148806037[54] = 0.0;
   out_3413546436148806037[55] = 0.0;
   out_3413546436148806037[56] = 0.0;
   out_3413546436148806037[57] = 1.0;
   out_3413546436148806037[58] = 0.0;
   out_3413546436148806037[59] = 0.0;
   out_3413546436148806037[60] = 0.0;
   out_3413546436148806037[61] = 0.0;
   out_3413546436148806037[62] = 0.0;
   out_3413546436148806037[63] = 0.0;
   out_3413546436148806037[64] = 0.0;
   out_3413546436148806037[65] = 0.0;
   out_3413546436148806037[66] = 0.0;
   out_3413546436148806037[67] = 0.0;
   out_3413546436148806037[68] = 0.0;
   out_3413546436148806037[69] = 0.0;
   out_3413546436148806037[70] = 0.0;
   out_3413546436148806037[71] = 0.0;
   out_3413546436148806037[72] = 0.0;
   out_3413546436148806037[73] = 0.0;
   out_3413546436148806037[74] = 0.0;
   out_3413546436148806037[75] = 0.0;
   out_3413546436148806037[76] = 1.0;
   out_3413546436148806037[77] = 0.0;
   out_3413546436148806037[78] = 0.0;
   out_3413546436148806037[79] = 0.0;
   out_3413546436148806037[80] = 0.0;
   out_3413546436148806037[81] = 0.0;
   out_3413546436148806037[82] = 0.0;
   out_3413546436148806037[83] = 0.0;
   out_3413546436148806037[84] = 0.0;
   out_3413546436148806037[85] = 0.0;
   out_3413546436148806037[86] = 0.0;
   out_3413546436148806037[87] = 0.0;
   out_3413546436148806037[88] = 0.0;
   out_3413546436148806037[89] = 0.0;
   out_3413546436148806037[90] = 0.0;
   out_3413546436148806037[91] = 0.0;
   out_3413546436148806037[92] = 0.0;
   out_3413546436148806037[93] = 0.0;
   out_3413546436148806037[94] = 0.0;
   out_3413546436148806037[95] = 1.0;
   out_3413546436148806037[96] = 0.0;
   out_3413546436148806037[97] = 0.0;
   out_3413546436148806037[98] = 0.0;
   out_3413546436148806037[99] = 0.0;
   out_3413546436148806037[100] = 0.0;
   out_3413546436148806037[101] = 0.0;
   out_3413546436148806037[102] = 0.0;
   out_3413546436148806037[103] = 0.0;
   out_3413546436148806037[104] = 0.0;
   out_3413546436148806037[105] = 0.0;
   out_3413546436148806037[106] = 0.0;
   out_3413546436148806037[107] = 0.0;
   out_3413546436148806037[108] = 0.0;
   out_3413546436148806037[109] = 0.0;
   out_3413546436148806037[110] = 0.0;
   out_3413546436148806037[111] = 0.0;
   out_3413546436148806037[112] = 0.0;
   out_3413546436148806037[113] = 0.0;
   out_3413546436148806037[114] = 1.0;
   out_3413546436148806037[115] = 0.0;
   out_3413546436148806037[116] = 0.0;
   out_3413546436148806037[117] = 0.0;
   out_3413546436148806037[118] = 0.0;
   out_3413546436148806037[119] = 0.0;
   out_3413546436148806037[120] = 0.0;
   out_3413546436148806037[121] = 0.0;
   out_3413546436148806037[122] = 0.0;
   out_3413546436148806037[123] = 0.0;
   out_3413546436148806037[124] = 0.0;
   out_3413546436148806037[125] = 0.0;
   out_3413546436148806037[126] = 0.0;
   out_3413546436148806037[127] = 0.0;
   out_3413546436148806037[128] = 0.0;
   out_3413546436148806037[129] = 0.0;
   out_3413546436148806037[130] = 0.0;
   out_3413546436148806037[131] = 0.0;
   out_3413546436148806037[132] = 0.0;
   out_3413546436148806037[133] = 1.0;
   out_3413546436148806037[134] = 0.0;
   out_3413546436148806037[135] = 0.0;
   out_3413546436148806037[136] = 0.0;
   out_3413546436148806037[137] = 0.0;
   out_3413546436148806037[138] = 0.0;
   out_3413546436148806037[139] = 0.0;
   out_3413546436148806037[140] = 0.0;
   out_3413546436148806037[141] = 0.0;
   out_3413546436148806037[142] = 0.0;
   out_3413546436148806037[143] = 0.0;
   out_3413546436148806037[144] = 0.0;
   out_3413546436148806037[145] = 0.0;
   out_3413546436148806037[146] = 0.0;
   out_3413546436148806037[147] = 0.0;
   out_3413546436148806037[148] = 0.0;
   out_3413546436148806037[149] = 0.0;
   out_3413546436148806037[150] = 0.0;
   out_3413546436148806037[151] = 0.0;
   out_3413546436148806037[152] = 1.0;
   out_3413546436148806037[153] = 0.0;
   out_3413546436148806037[154] = 0.0;
   out_3413546436148806037[155] = 0.0;
   out_3413546436148806037[156] = 0.0;
   out_3413546436148806037[157] = 0.0;
   out_3413546436148806037[158] = 0.0;
   out_3413546436148806037[159] = 0.0;
   out_3413546436148806037[160] = 0.0;
   out_3413546436148806037[161] = 0.0;
   out_3413546436148806037[162] = 0.0;
   out_3413546436148806037[163] = 0.0;
   out_3413546436148806037[164] = 0.0;
   out_3413546436148806037[165] = 0.0;
   out_3413546436148806037[166] = 0.0;
   out_3413546436148806037[167] = 0.0;
   out_3413546436148806037[168] = 0.0;
   out_3413546436148806037[169] = 0.0;
   out_3413546436148806037[170] = 0.0;
   out_3413546436148806037[171] = 1.0;
   out_3413546436148806037[172] = 0.0;
   out_3413546436148806037[173] = 0.0;
   out_3413546436148806037[174] = 0.0;
   out_3413546436148806037[175] = 0.0;
   out_3413546436148806037[176] = 0.0;
   out_3413546436148806037[177] = 0.0;
   out_3413546436148806037[178] = 0.0;
   out_3413546436148806037[179] = 0.0;
   out_3413546436148806037[180] = 0.0;
   out_3413546436148806037[181] = 0.0;
   out_3413546436148806037[182] = 0.0;
   out_3413546436148806037[183] = 0.0;
   out_3413546436148806037[184] = 0.0;
   out_3413546436148806037[185] = 0.0;
   out_3413546436148806037[186] = 0.0;
   out_3413546436148806037[187] = 0.0;
   out_3413546436148806037[188] = 0.0;
   out_3413546436148806037[189] = 0.0;
   out_3413546436148806037[190] = 1.0;
   out_3413546436148806037[191] = 0.0;
   out_3413546436148806037[192] = 0.0;
   out_3413546436148806037[193] = 0.0;
   out_3413546436148806037[194] = 0.0;
   out_3413546436148806037[195] = 0.0;
   out_3413546436148806037[196] = 0.0;
   out_3413546436148806037[197] = 0.0;
   out_3413546436148806037[198] = 0.0;
   out_3413546436148806037[199] = 0.0;
   out_3413546436148806037[200] = 0.0;
   out_3413546436148806037[201] = 0.0;
   out_3413546436148806037[202] = 0.0;
   out_3413546436148806037[203] = 0.0;
   out_3413546436148806037[204] = 0.0;
   out_3413546436148806037[205] = 0.0;
   out_3413546436148806037[206] = 0.0;
   out_3413546436148806037[207] = 0.0;
   out_3413546436148806037[208] = 0.0;
   out_3413546436148806037[209] = 1.0;
   out_3413546436148806037[210] = 0.0;
   out_3413546436148806037[211] = 0.0;
   out_3413546436148806037[212] = 0.0;
   out_3413546436148806037[213] = 0.0;
   out_3413546436148806037[214] = 0.0;
   out_3413546436148806037[215] = 0.0;
   out_3413546436148806037[216] = 0.0;
   out_3413546436148806037[217] = 0.0;
   out_3413546436148806037[218] = 0.0;
   out_3413546436148806037[219] = 0.0;
   out_3413546436148806037[220] = 0.0;
   out_3413546436148806037[221] = 0.0;
   out_3413546436148806037[222] = 0.0;
   out_3413546436148806037[223] = 0.0;
   out_3413546436148806037[224] = 0.0;
   out_3413546436148806037[225] = 0.0;
   out_3413546436148806037[226] = 0.0;
   out_3413546436148806037[227] = 0.0;
   out_3413546436148806037[228] = 1.0;
   out_3413546436148806037[229] = 0.0;
   out_3413546436148806037[230] = 0.0;
   out_3413546436148806037[231] = 0.0;
   out_3413546436148806037[232] = 0.0;
   out_3413546436148806037[233] = 0.0;
   out_3413546436148806037[234] = 0.0;
   out_3413546436148806037[235] = 0.0;
   out_3413546436148806037[236] = 0.0;
   out_3413546436148806037[237] = 0.0;
   out_3413546436148806037[238] = 0.0;
   out_3413546436148806037[239] = 0.0;
   out_3413546436148806037[240] = 0.0;
   out_3413546436148806037[241] = 0.0;
   out_3413546436148806037[242] = 0.0;
   out_3413546436148806037[243] = 0.0;
   out_3413546436148806037[244] = 0.0;
   out_3413546436148806037[245] = 0.0;
   out_3413546436148806037[246] = 0.0;
   out_3413546436148806037[247] = 1.0;
   out_3413546436148806037[248] = 0.0;
   out_3413546436148806037[249] = 0.0;
   out_3413546436148806037[250] = 0.0;
   out_3413546436148806037[251] = 0.0;
   out_3413546436148806037[252] = 0.0;
   out_3413546436148806037[253] = 0.0;
   out_3413546436148806037[254] = 0.0;
   out_3413546436148806037[255] = 0.0;
   out_3413546436148806037[256] = 0.0;
   out_3413546436148806037[257] = 0.0;
   out_3413546436148806037[258] = 0.0;
   out_3413546436148806037[259] = 0.0;
   out_3413546436148806037[260] = 0.0;
   out_3413546436148806037[261] = 0.0;
   out_3413546436148806037[262] = 0.0;
   out_3413546436148806037[263] = 0.0;
   out_3413546436148806037[264] = 0.0;
   out_3413546436148806037[265] = 0.0;
   out_3413546436148806037[266] = 1.0;
   out_3413546436148806037[267] = 0.0;
   out_3413546436148806037[268] = 0.0;
   out_3413546436148806037[269] = 0.0;
   out_3413546436148806037[270] = 0.0;
   out_3413546436148806037[271] = 0.0;
   out_3413546436148806037[272] = 0.0;
   out_3413546436148806037[273] = 0.0;
   out_3413546436148806037[274] = 0.0;
   out_3413546436148806037[275] = 0.0;
   out_3413546436148806037[276] = 0.0;
   out_3413546436148806037[277] = 0.0;
   out_3413546436148806037[278] = 0.0;
   out_3413546436148806037[279] = 0.0;
   out_3413546436148806037[280] = 0.0;
   out_3413546436148806037[281] = 0.0;
   out_3413546436148806037[282] = 0.0;
   out_3413546436148806037[283] = 0.0;
   out_3413546436148806037[284] = 0.0;
   out_3413546436148806037[285] = 1.0;
   out_3413546436148806037[286] = 0.0;
   out_3413546436148806037[287] = 0.0;
   out_3413546436148806037[288] = 0.0;
   out_3413546436148806037[289] = 0.0;
   out_3413546436148806037[290] = 0.0;
   out_3413546436148806037[291] = 0.0;
   out_3413546436148806037[292] = 0.0;
   out_3413546436148806037[293] = 0.0;
   out_3413546436148806037[294] = 0.0;
   out_3413546436148806037[295] = 0.0;
   out_3413546436148806037[296] = 0.0;
   out_3413546436148806037[297] = 0.0;
   out_3413546436148806037[298] = 0.0;
   out_3413546436148806037[299] = 0.0;
   out_3413546436148806037[300] = 0.0;
   out_3413546436148806037[301] = 0.0;
   out_3413546436148806037[302] = 0.0;
   out_3413546436148806037[303] = 0.0;
   out_3413546436148806037[304] = 1.0;
   out_3413546436148806037[305] = 0.0;
   out_3413546436148806037[306] = 0.0;
   out_3413546436148806037[307] = 0.0;
   out_3413546436148806037[308] = 0.0;
   out_3413546436148806037[309] = 0.0;
   out_3413546436148806037[310] = 0.0;
   out_3413546436148806037[311] = 0.0;
   out_3413546436148806037[312] = 0.0;
   out_3413546436148806037[313] = 0.0;
   out_3413546436148806037[314] = 0.0;
   out_3413546436148806037[315] = 0.0;
   out_3413546436148806037[316] = 0.0;
   out_3413546436148806037[317] = 0.0;
   out_3413546436148806037[318] = 0.0;
   out_3413546436148806037[319] = 0.0;
   out_3413546436148806037[320] = 0.0;
   out_3413546436148806037[321] = 0.0;
   out_3413546436148806037[322] = 0.0;
   out_3413546436148806037[323] = 1.0;
}
void f_fun(double *state, double dt, double *out_8715702946180776093) {
   out_8715702946180776093[0] = atan2((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), -(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]));
   out_8715702946180776093[1] = asin(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]));
   out_8715702946180776093[2] = atan2(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), -(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]));
   out_8715702946180776093[3] = dt*state[12] + state[3];
   out_8715702946180776093[4] = dt*state[13] + state[4];
   out_8715702946180776093[5] = dt*state[14] + state[5];
   out_8715702946180776093[6] = state[6];
   out_8715702946180776093[7] = state[7];
   out_8715702946180776093[8] = state[8];
   out_8715702946180776093[9] = state[9];
   out_8715702946180776093[10] = state[10];
   out_8715702946180776093[11] = state[11];
   out_8715702946180776093[12] = state[12];
   out_8715702946180776093[13] = state[13];
   out_8715702946180776093[14] = state[14];
   out_8715702946180776093[15] = state[15];
   out_8715702946180776093[16] = state[16];
   out_8715702946180776093[17] = state[17];
}
void F_fun(double *state, double dt, double *out_6806979793105738329) {
   out_6806979793105738329[0] = ((-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*cos(state[0])*cos(state[1]) - sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*cos(state[0])*cos(state[1]) - sin(dt*state[6])*sin(state[0])*cos(dt*state[7])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6806979793105738329[1] = ((-sin(dt*state[6])*sin(dt*state[8]) - sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*cos(state[1]) - (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*sin(state[1]) - sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(state[0]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*sin(state[1]) + (-sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) + sin(dt*state[8])*cos(dt*state[6]))*cos(state[1]) - sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(state[0]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6806979793105738329[2] = 0;
   out_6806979793105738329[3] = 0;
   out_6806979793105738329[4] = 0;
   out_6806979793105738329[5] = 0;
   out_6806979793105738329[6] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(dt*cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) - dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6806979793105738329[7] = (-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[6])*sin(dt*state[7])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[6])*sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) - dt*sin(dt*state[6])*sin(state[1])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + (-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))*(-dt*sin(dt*state[7])*cos(dt*state[6])*cos(state[0])*cos(state[1]) + dt*sin(dt*state[8])*sin(state[0])*cos(dt*state[6])*cos(dt*state[7])*cos(state[1]) - dt*sin(state[1])*cos(dt*state[6])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6806979793105738329[8] = ((dt*sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + dt*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (dt*sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]))*(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2)) + ((dt*sin(dt*state[6])*sin(dt*state[8]) + dt*sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (-dt*sin(dt*state[6])*cos(dt*state[8]) + dt*sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]))*(-(sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) + (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) - sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/(pow(-(sin(dt*state[6])*sin(dt*state[8]) + sin(dt*state[7])*cos(dt*state[6])*cos(dt*state[8]))*sin(state[1]) + (-sin(dt*state[6])*cos(dt*state[8]) + sin(dt*state[7])*sin(dt*state[8])*cos(dt*state[6]))*sin(state[0])*cos(state[1]) + cos(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2) + pow((sin(dt*state[6])*sin(dt*state[7])*sin(dt*state[8]) + cos(dt*state[6])*cos(dt*state[8]))*sin(state[0])*cos(state[1]) - (sin(dt*state[6])*sin(dt*state[7])*cos(dt*state[8]) - sin(dt*state[8])*cos(dt*state[6]))*sin(state[1]) + sin(dt*state[6])*cos(dt*state[7])*cos(state[0])*cos(state[1]), 2));
   out_6806979793105738329[9] = 0;
   out_6806979793105738329[10] = 0;
   out_6806979793105738329[11] = 0;
   out_6806979793105738329[12] = 0;
   out_6806979793105738329[13] = 0;
   out_6806979793105738329[14] = 0;
   out_6806979793105738329[15] = 0;
   out_6806979793105738329[16] = 0;
   out_6806979793105738329[17] = 0;
   out_6806979793105738329[18] = (-sin(dt*state[7])*sin(state[0])*cos(state[1]) - sin(dt*state[8])*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6806979793105738329[19] = (-sin(dt*state[7])*sin(state[1])*cos(state[0]) + sin(dt*state[8])*sin(state[0])*sin(state[1])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6806979793105738329[20] = 0;
   out_6806979793105738329[21] = 0;
   out_6806979793105738329[22] = 0;
   out_6806979793105738329[23] = 0;
   out_6806979793105738329[24] = 0;
   out_6806979793105738329[25] = (dt*sin(dt*state[7])*sin(dt*state[8])*sin(state[0])*cos(state[1]) - dt*sin(dt*state[7])*sin(state[1])*cos(dt*state[8]) + dt*cos(dt*state[7])*cos(state[0])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6806979793105738329[26] = (-dt*sin(dt*state[8])*sin(state[1])*cos(dt*state[7]) - dt*sin(state[0])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/sqrt(1 - pow(sin(dt*state[7])*cos(state[0])*cos(state[1]) - sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1]) + sin(state[1])*cos(dt*state[7])*cos(dt*state[8]), 2));
   out_6806979793105738329[27] = 0;
   out_6806979793105738329[28] = 0;
   out_6806979793105738329[29] = 0;
   out_6806979793105738329[30] = 0;
   out_6806979793105738329[31] = 0;
   out_6806979793105738329[32] = 0;
   out_6806979793105738329[33] = 0;
   out_6806979793105738329[34] = 0;
   out_6806979793105738329[35] = 0;
   out_6806979793105738329[36] = ((sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6806979793105738329[37] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-sin(dt*state[7])*sin(state[2])*cos(state[0])*cos(state[1]) + sin(dt*state[8])*sin(state[0])*sin(state[2])*cos(dt*state[7])*cos(state[1]) - sin(state[1])*sin(state[2])*cos(dt*state[7])*cos(dt*state[8]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(-sin(dt*state[7])*cos(state[0])*cos(state[1])*cos(state[2]) + sin(dt*state[8])*sin(state[0])*cos(dt*state[7])*cos(state[1])*cos(state[2]) - sin(state[1])*cos(dt*state[7])*cos(dt*state[8])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6806979793105738329[38] = ((-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (-sin(state[0])*sin(state[1])*sin(state[2]) - cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6806979793105738329[39] = 0;
   out_6806979793105738329[40] = 0;
   out_6806979793105738329[41] = 0;
   out_6806979793105738329[42] = 0;
   out_6806979793105738329[43] = (-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))*(dt*(sin(state[0])*cos(state[2]) - sin(state[1])*sin(state[2])*cos(state[0]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*sin(state[2])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + ((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))*(dt*(-sin(state[0])*sin(state[2]) - sin(state[1])*cos(state[0])*cos(state[2]))*cos(dt*state[7]) - dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[7])*sin(dt*state[8]) - dt*sin(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6806979793105738329[44] = (dt*(sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*sin(state[2])*cos(dt*state[7])*cos(state[1]))*(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2)) + (dt*(sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*cos(dt*state[7])*cos(dt*state[8]) - dt*sin(dt*state[8])*cos(dt*state[7])*cos(state[1])*cos(state[2]))*((-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) - (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) - sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]))/(pow(-(sin(state[0])*sin(state[2]) + sin(state[1])*cos(state[0])*cos(state[2]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*cos(state[2]) - sin(state[2])*cos(state[0]))*sin(dt*state[8])*cos(dt*state[7]) + cos(dt*state[7])*cos(dt*state[8])*cos(state[1])*cos(state[2]), 2) + pow(-(-sin(state[0])*cos(state[2]) + sin(state[1])*sin(state[2])*cos(state[0]))*sin(dt*state[7]) + (sin(state[0])*sin(state[1])*sin(state[2]) + cos(state[0])*cos(state[2]))*sin(dt*state[8])*cos(dt*state[7]) + sin(state[2])*cos(dt*state[7])*cos(dt*state[8])*cos(state[1]), 2));
   out_6806979793105738329[45] = 0;
   out_6806979793105738329[46] = 0;
   out_6806979793105738329[47] = 0;
   out_6806979793105738329[48] = 0;
   out_6806979793105738329[49] = 0;
   out_6806979793105738329[50] = 0;
   out_6806979793105738329[51] = 0;
   out_6806979793105738329[52] = 0;
   out_6806979793105738329[53] = 0;
   out_6806979793105738329[54] = 0;
   out_6806979793105738329[55] = 0;
   out_6806979793105738329[56] = 0;
   out_6806979793105738329[57] = 1;
   out_6806979793105738329[58] = 0;
   out_6806979793105738329[59] = 0;
   out_6806979793105738329[60] = 0;
   out_6806979793105738329[61] = 0;
   out_6806979793105738329[62] = 0;
   out_6806979793105738329[63] = 0;
   out_6806979793105738329[64] = 0;
   out_6806979793105738329[65] = 0;
   out_6806979793105738329[66] = dt;
   out_6806979793105738329[67] = 0;
   out_6806979793105738329[68] = 0;
   out_6806979793105738329[69] = 0;
   out_6806979793105738329[70] = 0;
   out_6806979793105738329[71] = 0;
   out_6806979793105738329[72] = 0;
   out_6806979793105738329[73] = 0;
   out_6806979793105738329[74] = 0;
   out_6806979793105738329[75] = 0;
   out_6806979793105738329[76] = 1;
   out_6806979793105738329[77] = 0;
   out_6806979793105738329[78] = 0;
   out_6806979793105738329[79] = 0;
   out_6806979793105738329[80] = 0;
   out_6806979793105738329[81] = 0;
   out_6806979793105738329[82] = 0;
   out_6806979793105738329[83] = 0;
   out_6806979793105738329[84] = 0;
   out_6806979793105738329[85] = dt;
   out_6806979793105738329[86] = 0;
   out_6806979793105738329[87] = 0;
   out_6806979793105738329[88] = 0;
   out_6806979793105738329[89] = 0;
   out_6806979793105738329[90] = 0;
   out_6806979793105738329[91] = 0;
   out_6806979793105738329[92] = 0;
   out_6806979793105738329[93] = 0;
   out_6806979793105738329[94] = 0;
   out_6806979793105738329[95] = 1;
   out_6806979793105738329[96] = 0;
   out_6806979793105738329[97] = 0;
   out_6806979793105738329[98] = 0;
   out_6806979793105738329[99] = 0;
   out_6806979793105738329[100] = 0;
   out_6806979793105738329[101] = 0;
   out_6806979793105738329[102] = 0;
   out_6806979793105738329[103] = 0;
   out_6806979793105738329[104] = dt;
   out_6806979793105738329[105] = 0;
   out_6806979793105738329[106] = 0;
   out_6806979793105738329[107] = 0;
   out_6806979793105738329[108] = 0;
   out_6806979793105738329[109] = 0;
   out_6806979793105738329[110] = 0;
   out_6806979793105738329[111] = 0;
   out_6806979793105738329[112] = 0;
   out_6806979793105738329[113] = 0;
   out_6806979793105738329[114] = 1;
   out_6806979793105738329[115] = 0;
   out_6806979793105738329[116] = 0;
   out_6806979793105738329[117] = 0;
   out_6806979793105738329[118] = 0;
   out_6806979793105738329[119] = 0;
   out_6806979793105738329[120] = 0;
   out_6806979793105738329[121] = 0;
   out_6806979793105738329[122] = 0;
   out_6806979793105738329[123] = 0;
   out_6806979793105738329[124] = 0;
   out_6806979793105738329[125] = 0;
   out_6806979793105738329[126] = 0;
   out_6806979793105738329[127] = 0;
   out_6806979793105738329[128] = 0;
   out_6806979793105738329[129] = 0;
   out_6806979793105738329[130] = 0;
   out_6806979793105738329[131] = 0;
   out_6806979793105738329[132] = 0;
   out_6806979793105738329[133] = 1;
   out_6806979793105738329[134] = 0;
   out_6806979793105738329[135] = 0;
   out_6806979793105738329[136] = 0;
   out_6806979793105738329[137] = 0;
   out_6806979793105738329[138] = 0;
   out_6806979793105738329[139] = 0;
   out_6806979793105738329[140] = 0;
   out_6806979793105738329[141] = 0;
   out_6806979793105738329[142] = 0;
   out_6806979793105738329[143] = 0;
   out_6806979793105738329[144] = 0;
   out_6806979793105738329[145] = 0;
   out_6806979793105738329[146] = 0;
   out_6806979793105738329[147] = 0;
   out_6806979793105738329[148] = 0;
   out_6806979793105738329[149] = 0;
   out_6806979793105738329[150] = 0;
   out_6806979793105738329[151] = 0;
   out_6806979793105738329[152] = 1;
   out_6806979793105738329[153] = 0;
   out_6806979793105738329[154] = 0;
   out_6806979793105738329[155] = 0;
   out_6806979793105738329[156] = 0;
   out_6806979793105738329[157] = 0;
   out_6806979793105738329[158] = 0;
   out_6806979793105738329[159] = 0;
   out_6806979793105738329[160] = 0;
   out_6806979793105738329[161] = 0;
   out_6806979793105738329[162] = 0;
   out_6806979793105738329[163] = 0;
   out_6806979793105738329[164] = 0;
   out_6806979793105738329[165] = 0;
   out_6806979793105738329[166] = 0;
   out_6806979793105738329[167] = 0;
   out_6806979793105738329[168] = 0;
   out_6806979793105738329[169] = 0;
   out_6806979793105738329[170] = 0;
   out_6806979793105738329[171] = 1;
   out_6806979793105738329[172] = 0;
   out_6806979793105738329[173] = 0;
   out_6806979793105738329[174] = 0;
   out_6806979793105738329[175] = 0;
   out_6806979793105738329[176] = 0;
   out_6806979793105738329[177] = 0;
   out_6806979793105738329[178] = 0;
   out_6806979793105738329[179] = 0;
   out_6806979793105738329[180] = 0;
   out_6806979793105738329[181] = 0;
   out_6806979793105738329[182] = 0;
   out_6806979793105738329[183] = 0;
   out_6806979793105738329[184] = 0;
   out_6806979793105738329[185] = 0;
   out_6806979793105738329[186] = 0;
   out_6806979793105738329[187] = 0;
   out_6806979793105738329[188] = 0;
   out_6806979793105738329[189] = 0;
   out_6806979793105738329[190] = 1;
   out_6806979793105738329[191] = 0;
   out_6806979793105738329[192] = 0;
   out_6806979793105738329[193] = 0;
   out_6806979793105738329[194] = 0;
   out_6806979793105738329[195] = 0;
   out_6806979793105738329[196] = 0;
   out_6806979793105738329[197] = 0;
   out_6806979793105738329[198] = 0;
   out_6806979793105738329[199] = 0;
   out_6806979793105738329[200] = 0;
   out_6806979793105738329[201] = 0;
   out_6806979793105738329[202] = 0;
   out_6806979793105738329[203] = 0;
   out_6806979793105738329[204] = 0;
   out_6806979793105738329[205] = 0;
   out_6806979793105738329[206] = 0;
   out_6806979793105738329[207] = 0;
   out_6806979793105738329[208] = 0;
   out_6806979793105738329[209] = 1;
   out_6806979793105738329[210] = 0;
   out_6806979793105738329[211] = 0;
   out_6806979793105738329[212] = 0;
   out_6806979793105738329[213] = 0;
   out_6806979793105738329[214] = 0;
   out_6806979793105738329[215] = 0;
   out_6806979793105738329[216] = 0;
   out_6806979793105738329[217] = 0;
   out_6806979793105738329[218] = 0;
   out_6806979793105738329[219] = 0;
   out_6806979793105738329[220] = 0;
   out_6806979793105738329[221] = 0;
   out_6806979793105738329[222] = 0;
   out_6806979793105738329[223] = 0;
   out_6806979793105738329[224] = 0;
   out_6806979793105738329[225] = 0;
   out_6806979793105738329[226] = 0;
   out_6806979793105738329[227] = 0;
   out_6806979793105738329[228] = 1;
   out_6806979793105738329[229] = 0;
   out_6806979793105738329[230] = 0;
   out_6806979793105738329[231] = 0;
   out_6806979793105738329[232] = 0;
   out_6806979793105738329[233] = 0;
   out_6806979793105738329[234] = 0;
   out_6806979793105738329[235] = 0;
   out_6806979793105738329[236] = 0;
   out_6806979793105738329[237] = 0;
   out_6806979793105738329[238] = 0;
   out_6806979793105738329[239] = 0;
   out_6806979793105738329[240] = 0;
   out_6806979793105738329[241] = 0;
   out_6806979793105738329[242] = 0;
   out_6806979793105738329[243] = 0;
   out_6806979793105738329[244] = 0;
   out_6806979793105738329[245] = 0;
   out_6806979793105738329[246] = 0;
   out_6806979793105738329[247] = 1;
   out_6806979793105738329[248] = 0;
   out_6806979793105738329[249] = 0;
   out_6806979793105738329[250] = 0;
   out_6806979793105738329[251] = 0;
   out_6806979793105738329[252] = 0;
   out_6806979793105738329[253] = 0;
   out_6806979793105738329[254] = 0;
   out_6806979793105738329[255] = 0;
   out_6806979793105738329[256] = 0;
   out_6806979793105738329[257] = 0;
   out_6806979793105738329[258] = 0;
   out_6806979793105738329[259] = 0;
   out_6806979793105738329[260] = 0;
   out_6806979793105738329[261] = 0;
   out_6806979793105738329[262] = 0;
   out_6806979793105738329[263] = 0;
   out_6806979793105738329[264] = 0;
   out_6806979793105738329[265] = 0;
   out_6806979793105738329[266] = 1;
   out_6806979793105738329[267] = 0;
   out_6806979793105738329[268] = 0;
   out_6806979793105738329[269] = 0;
   out_6806979793105738329[270] = 0;
   out_6806979793105738329[271] = 0;
   out_6806979793105738329[272] = 0;
   out_6806979793105738329[273] = 0;
   out_6806979793105738329[274] = 0;
   out_6806979793105738329[275] = 0;
   out_6806979793105738329[276] = 0;
   out_6806979793105738329[277] = 0;
   out_6806979793105738329[278] = 0;
   out_6806979793105738329[279] = 0;
   out_6806979793105738329[280] = 0;
   out_6806979793105738329[281] = 0;
   out_6806979793105738329[282] = 0;
   out_6806979793105738329[283] = 0;
   out_6806979793105738329[284] = 0;
   out_6806979793105738329[285] = 1;
   out_6806979793105738329[286] = 0;
   out_6806979793105738329[287] = 0;
   out_6806979793105738329[288] = 0;
   out_6806979793105738329[289] = 0;
   out_6806979793105738329[290] = 0;
   out_6806979793105738329[291] = 0;
   out_6806979793105738329[292] = 0;
   out_6806979793105738329[293] = 0;
   out_6806979793105738329[294] = 0;
   out_6806979793105738329[295] = 0;
   out_6806979793105738329[296] = 0;
   out_6806979793105738329[297] = 0;
   out_6806979793105738329[298] = 0;
   out_6806979793105738329[299] = 0;
   out_6806979793105738329[300] = 0;
   out_6806979793105738329[301] = 0;
   out_6806979793105738329[302] = 0;
   out_6806979793105738329[303] = 0;
   out_6806979793105738329[304] = 1;
   out_6806979793105738329[305] = 0;
   out_6806979793105738329[306] = 0;
   out_6806979793105738329[307] = 0;
   out_6806979793105738329[308] = 0;
   out_6806979793105738329[309] = 0;
   out_6806979793105738329[310] = 0;
   out_6806979793105738329[311] = 0;
   out_6806979793105738329[312] = 0;
   out_6806979793105738329[313] = 0;
   out_6806979793105738329[314] = 0;
   out_6806979793105738329[315] = 0;
   out_6806979793105738329[316] = 0;
   out_6806979793105738329[317] = 0;
   out_6806979793105738329[318] = 0;
   out_6806979793105738329[319] = 0;
   out_6806979793105738329[320] = 0;
   out_6806979793105738329[321] = 0;
   out_6806979793105738329[322] = 0;
   out_6806979793105738329[323] = 1;
}
void h_4(double *state, double *unused, double *out_5766790488282858427) {
   out_5766790488282858427[0] = state[6] + state[9];
   out_5766790488282858427[1] = state[7] + state[10];
   out_5766790488282858427[2] = state[8] + state[11];
}
void H_4(double *state, double *unused, double *out_6784399393215802223) {
   out_6784399393215802223[0] = 0;
   out_6784399393215802223[1] = 0;
   out_6784399393215802223[2] = 0;
   out_6784399393215802223[3] = 0;
   out_6784399393215802223[4] = 0;
   out_6784399393215802223[5] = 0;
   out_6784399393215802223[6] = 1;
   out_6784399393215802223[7] = 0;
   out_6784399393215802223[8] = 0;
   out_6784399393215802223[9] = 1;
   out_6784399393215802223[10] = 0;
   out_6784399393215802223[11] = 0;
   out_6784399393215802223[12] = 0;
   out_6784399393215802223[13] = 0;
   out_6784399393215802223[14] = 0;
   out_6784399393215802223[15] = 0;
   out_6784399393215802223[16] = 0;
   out_6784399393215802223[17] = 0;
   out_6784399393215802223[18] = 0;
   out_6784399393215802223[19] = 0;
   out_6784399393215802223[20] = 0;
   out_6784399393215802223[21] = 0;
   out_6784399393215802223[22] = 0;
   out_6784399393215802223[23] = 0;
   out_6784399393215802223[24] = 0;
   out_6784399393215802223[25] = 1;
   out_6784399393215802223[26] = 0;
   out_6784399393215802223[27] = 0;
   out_6784399393215802223[28] = 1;
   out_6784399393215802223[29] = 0;
   out_6784399393215802223[30] = 0;
   out_6784399393215802223[31] = 0;
   out_6784399393215802223[32] = 0;
   out_6784399393215802223[33] = 0;
   out_6784399393215802223[34] = 0;
   out_6784399393215802223[35] = 0;
   out_6784399393215802223[36] = 0;
   out_6784399393215802223[37] = 0;
   out_6784399393215802223[38] = 0;
   out_6784399393215802223[39] = 0;
   out_6784399393215802223[40] = 0;
   out_6784399393215802223[41] = 0;
   out_6784399393215802223[42] = 0;
   out_6784399393215802223[43] = 0;
   out_6784399393215802223[44] = 1;
   out_6784399393215802223[45] = 0;
   out_6784399393215802223[46] = 0;
   out_6784399393215802223[47] = 1;
   out_6784399393215802223[48] = 0;
   out_6784399393215802223[49] = 0;
   out_6784399393215802223[50] = 0;
   out_6784399393215802223[51] = 0;
   out_6784399393215802223[52] = 0;
   out_6784399393215802223[53] = 0;
}
void h_10(double *state, double *unused, double *out_5252621184145006782) {
   out_5252621184145006782[0] = 9.8100000000000005*sin(state[1]) - state[4]*state[8] + state[5]*state[7] + state[12] + state[15];
   out_5252621184145006782[1] = -9.8100000000000005*sin(state[0])*cos(state[1]) + state[3]*state[8] - state[5]*state[6] + state[13] + state[16];
   out_5252621184145006782[2] = -9.8100000000000005*cos(state[0])*cos(state[1]) - state[3]*state[7] + state[4]*state[6] + state[14] + state[17];
}
void H_10(double *state, double *unused, double *out_6050564803174162078) {
   out_6050564803174162078[0] = 0;
   out_6050564803174162078[1] = 9.8100000000000005*cos(state[1]);
   out_6050564803174162078[2] = 0;
   out_6050564803174162078[3] = 0;
   out_6050564803174162078[4] = -state[8];
   out_6050564803174162078[5] = state[7];
   out_6050564803174162078[6] = 0;
   out_6050564803174162078[7] = state[5];
   out_6050564803174162078[8] = -state[4];
   out_6050564803174162078[9] = 0;
   out_6050564803174162078[10] = 0;
   out_6050564803174162078[11] = 0;
   out_6050564803174162078[12] = 1;
   out_6050564803174162078[13] = 0;
   out_6050564803174162078[14] = 0;
   out_6050564803174162078[15] = 1;
   out_6050564803174162078[16] = 0;
   out_6050564803174162078[17] = 0;
   out_6050564803174162078[18] = -9.8100000000000005*cos(state[0])*cos(state[1]);
   out_6050564803174162078[19] = 9.8100000000000005*sin(state[0])*sin(state[1]);
   out_6050564803174162078[20] = 0;
   out_6050564803174162078[21] = state[8];
   out_6050564803174162078[22] = 0;
   out_6050564803174162078[23] = -state[6];
   out_6050564803174162078[24] = -state[5];
   out_6050564803174162078[25] = 0;
   out_6050564803174162078[26] = state[3];
   out_6050564803174162078[27] = 0;
   out_6050564803174162078[28] = 0;
   out_6050564803174162078[29] = 0;
   out_6050564803174162078[30] = 0;
   out_6050564803174162078[31] = 1;
   out_6050564803174162078[32] = 0;
   out_6050564803174162078[33] = 0;
   out_6050564803174162078[34] = 1;
   out_6050564803174162078[35] = 0;
   out_6050564803174162078[36] = 9.8100000000000005*sin(state[0])*cos(state[1]);
   out_6050564803174162078[37] = 9.8100000000000005*sin(state[1])*cos(state[0]);
   out_6050564803174162078[38] = 0;
   out_6050564803174162078[39] = -state[7];
   out_6050564803174162078[40] = state[6];
   out_6050564803174162078[41] = 0;
   out_6050564803174162078[42] = state[4];
   out_6050564803174162078[43] = -state[3];
   out_6050564803174162078[44] = 0;
   out_6050564803174162078[45] = 0;
   out_6050564803174162078[46] = 0;
   out_6050564803174162078[47] = 0;
   out_6050564803174162078[48] = 0;
   out_6050564803174162078[49] = 0;
   out_6050564803174162078[50] = 1;
   out_6050564803174162078[51] = 0;
   out_6050564803174162078[52] = 0;
   out_6050564803174162078[53] = 1;
}
void h_13(double *state, double *unused, double *out_6589030393907913922) {
   out_6589030393907913922[0] = state[3];
   out_6589030393907913922[1] = state[4];
   out_6589030393907913922[2] = state[5];
}
void H_13(double *state, double *unused, double *out_3572125567883469422) {
   out_3572125567883469422[0] = 0;
   out_3572125567883469422[1] = 0;
   out_3572125567883469422[2] = 0;
   out_3572125567883469422[3] = 1;
   out_3572125567883469422[4] = 0;
   out_3572125567883469422[5] = 0;
   out_3572125567883469422[6] = 0;
   out_3572125567883469422[7] = 0;
   out_3572125567883469422[8] = 0;
   out_3572125567883469422[9] = 0;
   out_3572125567883469422[10] = 0;
   out_3572125567883469422[11] = 0;
   out_3572125567883469422[12] = 0;
   out_3572125567883469422[13] = 0;
   out_3572125567883469422[14] = 0;
   out_3572125567883469422[15] = 0;
   out_3572125567883469422[16] = 0;
   out_3572125567883469422[17] = 0;
   out_3572125567883469422[18] = 0;
   out_3572125567883469422[19] = 0;
   out_3572125567883469422[20] = 0;
   out_3572125567883469422[21] = 0;
   out_3572125567883469422[22] = 1;
   out_3572125567883469422[23] = 0;
   out_3572125567883469422[24] = 0;
   out_3572125567883469422[25] = 0;
   out_3572125567883469422[26] = 0;
   out_3572125567883469422[27] = 0;
   out_3572125567883469422[28] = 0;
   out_3572125567883469422[29] = 0;
   out_3572125567883469422[30] = 0;
   out_3572125567883469422[31] = 0;
   out_3572125567883469422[32] = 0;
   out_3572125567883469422[33] = 0;
   out_3572125567883469422[34] = 0;
   out_3572125567883469422[35] = 0;
   out_3572125567883469422[36] = 0;
   out_3572125567883469422[37] = 0;
   out_3572125567883469422[38] = 0;
   out_3572125567883469422[39] = 0;
   out_3572125567883469422[40] = 0;
   out_3572125567883469422[41] = 1;
   out_3572125567883469422[42] = 0;
   out_3572125567883469422[43] = 0;
   out_3572125567883469422[44] = 0;
   out_3572125567883469422[45] = 0;
   out_3572125567883469422[46] = 0;
   out_3572125567883469422[47] = 0;
   out_3572125567883469422[48] = 0;
   out_3572125567883469422[49] = 0;
   out_3572125567883469422[50] = 0;
   out_3572125567883469422[51] = 0;
   out_3572125567883469422[52] = 0;
   out_3572125567883469422[53] = 0;
}
void h_14(double *state, double *unused, double *out_3710584459584419169) {
   out_3710584459584419169[0] = state[6];
   out_3710584459584419169[1] = state[7];
   out_3710584459584419169[2] = state[8];
}
void H_14(double *state, double *unused, double *out_2821158536876317694) {
   out_2821158536876317694[0] = 0;
   out_2821158536876317694[1] = 0;
   out_2821158536876317694[2] = 0;
   out_2821158536876317694[3] = 0;
   out_2821158536876317694[4] = 0;
   out_2821158536876317694[5] = 0;
   out_2821158536876317694[6] = 1;
   out_2821158536876317694[7] = 0;
   out_2821158536876317694[8] = 0;
   out_2821158536876317694[9] = 0;
   out_2821158536876317694[10] = 0;
   out_2821158536876317694[11] = 0;
   out_2821158536876317694[12] = 0;
   out_2821158536876317694[13] = 0;
   out_2821158536876317694[14] = 0;
   out_2821158536876317694[15] = 0;
   out_2821158536876317694[16] = 0;
   out_2821158536876317694[17] = 0;
   out_2821158536876317694[18] = 0;
   out_2821158536876317694[19] = 0;
   out_2821158536876317694[20] = 0;
   out_2821158536876317694[21] = 0;
   out_2821158536876317694[22] = 0;
   out_2821158536876317694[23] = 0;
   out_2821158536876317694[24] = 0;
   out_2821158536876317694[25] = 1;
   out_2821158536876317694[26] = 0;
   out_2821158536876317694[27] = 0;
   out_2821158536876317694[28] = 0;
   out_2821158536876317694[29] = 0;
   out_2821158536876317694[30] = 0;
   out_2821158536876317694[31] = 0;
   out_2821158536876317694[32] = 0;
   out_2821158536876317694[33] = 0;
   out_2821158536876317694[34] = 0;
   out_2821158536876317694[35] = 0;
   out_2821158536876317694[36] = 0;
   out_2821158536876317694[37] = 0;
   out_2821158536876317694[38] = 0;
   out_2821158536876317694[39] = 0;
   out_2821158536876317694[40] = 0;
   out_2821158536876317694[41] = 0;
   out_2821158536876317694[42] = 0;
   out_2821158536876317694[43] = 0;
   out_2821158536876317694[44] = 1;
   out_2821158536876317694[45] = 0;
   out_2821158536876317694[46] = 0;
   out_2821158536876317694[47] = 0;
   out_2821158536876317694[48] = 0;
   out_2821158536876317694[49] = 0;
   out_2821158536876317694[50] = 0;
   out_2821158536876317694[51] = 0;
   out_2821158536876317694[52] = 0;
   out_2821158536876317694[53] = 0;
}
#include <eigen3/Eigen/Dense>
#include <iostream>

typedef Eigen::Matrix<double, DIM, DIM, Eigen::RowMajor> DDM;
typedef Eigen::Matrix<double, EDIM, EDIM, Eigen::RowMajor> EEM;
typedef Eigen::Matrix<double, DIM, EDIM, Eigen::RowMajor> DEM;

void predict(double *in_x, double *in_P, double *in_Q, double dt) {
  typedef Eigen::Matrix<double, MEDIM, MEDIM, Eigen::RowMajor> RRM;

  double nx[DIM] = {0};
  double in_F[EDIM*EDIM] = {0};

  // functions from sympy
  f_fun(in_x, dt, nx);
  F_fun(in_x, dt, in_F);


  EEM F(in_F);
  EEM P(in_P);
  EEM Q(in_Q);

  RRM F_main = F.topLeftCorner(MEDIM, MEDIM);
  P.topLeftCorner(MEDIM, MEDIM) = (F_main * P.topLeftCorner(MEDIM, MEDIM)) * F_main.transpose();
  P.topRightCorner(MEDIM, EDIM - MEDIM) = F_main * P.topRightCorner(MEDIM, EDIM - MEDIM);
  P.bottomLeftCorner(EDIM - MEDIM, MEDIM) = P.bottomLeftCorner(EDIM - MEDIM, MEDIM) * F_main.transpose();

  P = P + dt*Q;

  // copy out state
  memcpy(in_x, nx, DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
}

// note: extra_args dim only correct when null space projecting
// otherwise 1
template <int ZDIM, int EADIM, bool MAHA_TEST>
void update(double *in_x, double *in_P, Hfun h_fun, Hfun H_fun, Hfun Hea_fun, double *in_z, double *in_R, double *in_ea, double MAHA_THRESHOLD) {
  typedef Eigen::Matrix<double, ZDIM, ZDIM, Eigen::RowMajor> ZZM;
  typedef Eigen::Matrix<double, ZDIM, DIM, Eigen::RowMajor> ZDM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, EDIM, Eigen::RowMajor> XEM;
  //typedef Eigen::Matrix<double, EDIM, ZDIM, Eigen::RowMajor> EZM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, 1> X1M;
  typedef Eigen::Matrix<double, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor> XXM;

  double in_hx[ZDIM] = {0};
  double in_H[ZDIM * DIM] = {0};
  double in_H_mod[EDIM * DIM] = {0};
  double delta_x[EDIM] = {0};
  double x_new[DIM] = {0};


  // state x, P
  Eigen::Matrix<double, ZDIM, 1> z(in_z);
  EEM P(in_P);
  ZZM pre_R(in_R);

  // functions from sympy
  h_fun(in_x, in_ea, in_hx);
  H_fun(in_x, in_ea, in_H);
  ZDM pre_H(in_H);

  // get y (y = z - hx)
  Eigen::Matrix<double, ZDIM, 1> pre_y(in_hx); pre_y = z - pre_y;
  X1M y; XXM H; XXM R;
  if (Hea_fun){
    typedef Eigen::Matrix<double, ZDIM, EADIM, Eigen::RowMajor> ZAM;
    double in_Hea[ZDIM * EADIM] = {0};
    Hea_fun(in_x, in_ea, in_Hea);
    ZAM Hea(in_Hea);
    XXM A = Hea.transpose().fullPivLu().kernel();


    y = A.transpose() * pre_y;
    H = A.transpose() * pre_H;
    R = A.transpose() * pre_R * A;
  } else {
    y = pre_y;
    H = pre_H;
    R = pre_R;
  }
  // get modified H
  H_mod_fun(in_x, in_H_mod);
  DEM H_mod(in_H_mod);
  XEM H_err = H * H_mod;

  // Do mahalobis distance test
  if (MAHA_TEST){
    XXM a = (H_err * P * H_err.transpose() + R).inverse();
    double maha_dist = y.transpose() * a * y;
    if (maha_dist > MAHA_THRESHOLD){
      R = 1.0e16 * R;
    }
  }

  // Outlier resilient weighting
  double weight = 1;//(1.5)/(1 + y.squaredNorm()/R.sum());

  // kalman gains and I_KH
  XXM S = ((H_err * P) * H_err.transpose()) + R/weight;
  XEM KT = S.fullPivLu().solve(H_err * P.transpose());
  //EZM K = KT.transpose(); TODO: WHY DOES THIS NOT COMPILE?
  //EZM K = S.fullPivLu().solve(H_err * P.transpose()).transpose();
  //std::cout << "Here is the matrix rot:\n" << K << std::endl;
  EEM I_KH = Eigen::Matrix<double, EDIM, EDIM>::Identity() - (KT.transpose() * H_err);

  // update state by injecting dx
  Eigen::Matrix<double, EDIM, 1> dx(delta_x);
  dx  = (KT.transpose() * y);
  memcpy(delta_x, dx.data(), EDIM * sizeof(double));
  err_fun(in_x, delta_x, x_new);
  Eigen::Matrix<double, DIM, 1> x(x_new);

  // update cov
  P = ((I_KH * P) * I_KH.transpose()) + ((KT.transpose() * R) * KT);

  // copy out state
  memcpy(in_x, x.data(), DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
  memcpy(in_z, y.data(), y.rows() * sizeof(double));
}




}
extern "C" {

void pose_update_4(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_4, H_4, NULL, in_z, in_R, in_ea, MAHA_THRESH_4);
}
void pose_update_10(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_10, H_10, NULL, in_z, in_R, in_ea, MAHA_THRESH_10);
}
void pose_update_13(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_13, H_13, NULL, in_z, in_R, in_ea, MAHA_THRESH_13);
}
void pose_update_14(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<3, 3, 0>(in_x, in_P, h_14, H_14, NULL, in_z, in_R, in_ea, MAHA_THRESH_14);
}
void pose_err_fun(double *nom_x, double *delta_x, double *out_3654460514432875415) {
  err_fun(nom_x, delta_x, out_3654460514432875415);
}
void pose_inv_err_fun(double *nom_x, double *true_x, double *out_5462197318257341854) {
  inv_err_fun(nom_x, true_x, out_5462197318257341854);
}
void pose_H_mod_fun(double *state, double *out_3413546436148806037) {
  H_mod_fun(state, out_3413546436148806037);
}
void pose_f_fun(double *state, double dt, double *out_8715702946180776093) {
  f_fun(state,  dt, out_8715702946180776093);
}
void pose_F_fun(double *state, double dt, double *out_6806979793105738329) {
  F_fun(state,  dt, out_6806979793105738329);
}
void pose_h_4(double *state, double *unused, double *out_5766790488282858427) {
  h_4(state, unused, out_5766790488282858427);
}
void pose_H_4(double *state, double *unused, double *out_6784399393215802223) {
  H_4(state, unused, out_6784399393215802223);
}
void pose_h_10(double *state, double *unused, double *out_5252621184145006782) {
  h_10(state, unused, out_5252621184145006782);
}
void pose_H_10(double *state, double *unused, double *out_6050564803174162078) {
  H_10(state, unused, out_6050564803174162078);
}
void pose_h_13(double *state, double *unused, double *out_6589030393907913922) {
  h_13(state, unused, out_6589030393907913922);
}
void pose_H_13(double *state, double *unused, double *out_3572125567883469422) {
  H_13(state, unused, out_3572125567883469422);
}
void pose_h_14(double *state, double *unused, double *out_3710584459584419169) {
  h_14(state, unused, out_3710584459584419169);
}
void pose_H_14(double *state, double *unused, double *out_2821158536876317694) {
  H_14(state, unused, out_2821158536876317694);
}
void pose_predict(double *in_x, double *in_P, double *in_Q, double dt) {
  predict(in_x, in_P, in_Q, dt);
}
}

const EKF pose = {
  .name = "pose",
  .kinds = { 4, 10, 13, 14 },
  .feature_kinds = {  },
  .f_fun = pose_f_fun,
  .F_fun = pose_F_fun,
  .err_fun = pose_err_fun,
  .inv_err_fun = pose_inv_err_fun,
  .H_mod_fun = pose_H_mod_fun,
  .predict = pose_predict,
  .hs = {
    { 4, pose_h_4 },
    { 10, pose_h_10 },
    { 13, pose_h_13 },
    { 14, pose_h_14 },
  },
  .Hs = {
    { 4, pose_H_4 },
    { 10, pose_H_10 },
    { 13, pose_H_13 },
    { 14, pose_H_14 },
  },
  .updates = {
    { 4, pose_update_4 },
    { 10, pose_update_10 },
    { 13, pose_update_13 },
    { 14, pose_update_14 },
  },
  .Hes = {
  },
  .sets = {
  },
  .extra_routines = {
  },
};

ekf_lib_init(pose)
