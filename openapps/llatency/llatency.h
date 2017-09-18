#ifndef __LLATENCY_H
#define __LLATENCY_H

#include "openudp.h"

//=========================== variables =======================================

typedef struct {
   uint16_t             counter;  ///< incrementing counter which is written into the packet
   udp_resource_desc_t     desc;  ///< resource descriptor for this module, used to register at UDP stack
} llatency_vars_t;

//=========================== prototypes ======================================

void llatency_init(void);
void llatency_sendDone(OpenQueueEntry_t* msg, owerror_t error);
void llatency_receive(OpenQueueEntry_t* msg);
void llatency_get_values(uint32_t* values);

void llatency_send_pkt(void);
void llatency_task_cb(void);

#endif

