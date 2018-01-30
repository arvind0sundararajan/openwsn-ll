#include "opendefs.h"
#include "llatency.h"
#include "openbridge.h"
#include "openqueue.h"
#include "openserial.h"
#include "opentimers.h"
#include "packetfunctions.h"
#include "scheduler.h"
#include "IEEE802154E.h"
#include "idmanager.h"
#include "debugpins.h"
#include "headers/hw_memmap.h"
#include "source/gpio.h"
#include "board_info.h"
#include "leds.h"

//=========================== variables =======================================

llatency_vars_t llatency_vars;

static const uint8_t llatency_payload[]    = "llatency";

//the destination address must include the last 4 bytes of the RX mote
static const uint8_t llatency_dst_addr[]   = {
   0xbb, 0xbb, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
   0x00, 0x12, 0x4b, 0x00, 0x03, 0xa5, 0x90, 0xd5
}; 


//=========================== prototypes =======================================

static void ll_configure_pins(void);
void openmote_GPIO_A_Handler(void);

//=========================== public ==========================================

void llatency_init() {
   
    // clear local variables
    memset(&llatency_vars,0,sizeof(llatency_vars_t));

    // register at UDP stack
    llatency_vars.desc.port              = WKP_UDP_INJECT;
    llatency_vars.desc.callbackReceive   = &llatency_receive;
    llatency_vars.desc.callbackSendDone  = &llatency_sendDone;
    openudp_register(&llatency_vars.desc);

    // register the interrupt handler to openmote AD4/DIO4 (PA2)
    // configure CTS/DIO7 (PA3) to output spike on packet reception event (do we do that here?)
    ll_configure_pins();

    // uncomment this line to transmit over only one channel
    //ieee154e_setSingleChannel(11);
}

/* Register the interrupt handler to AD4/DIO4 (PA2)
 */
static void ll_configure_pins(void) {
    volatile uint32_t i;

    //Delay to avoid pin floating problems 
    for (i = 0xFFFF; i != 0; i--);

    // disable interrupts for PA2
    GPIOPinIntDisable(GPIO_A_BASE, GPIO_PIN_2);
    // clear the interrupt for PA2
    GPIOPinIntClear(GPIO_A_BASE, GPIO_PIN_2);

    // configures PA2 to be GPIO input
    GPIOPinTypeGPIOInput(GPIO_A_BASE, GPIO_PIN_2);

    // input GPIO on rising edge
    GPIOIntTypeSet(GPIO_A_BASE, GPIO_PIN_2, GPIO_RISING_EDGE);

    // register the port level interrupt handler
    GPIOPortIntRegister(GPIO_A_BASE, openmote_GPIO_A_Handler);

    // clear pin
    GPIOPinIntClear(GPIO_A_BASE, GPIO_PIN_2);
    // enable the interrupt (unmasks the interrupt bit)
    GPIOPinIntEnable(GPIO_A_BASE, GPIO_PIN_2);
}

void llatency_sendDone(OpenQueueEntry_t* msg, owerror_t error) {
   openqueue_freePacketBuffer(msg);
}

void llatency_receive(OpenQueueEntry_t* pkt) {
   debugpins_exp_toggle();

   // if dagroot, print over data (only dagroot is connected to serial)
   //openserial_printData((uint8_t*)(pkt->payload),pkt->length);
   openbridge_receive(pkt);

   //openqueue_freePacketBuffer(pkt);

   /*
   openserial_printError(
      COMPONENT_LLATENCY,
      ERR_RCVD_ECHO_REPLY,
      (errorparameter_t)0,
      (errorparameter_t)0
   );
   */
}

void llatency_get_values(uint32_t* values) {
  //counter value
  values[0] = opentimers_getValue();
  // asn
  values[1] = ieee154e_getStartOfSlotReference();
}

//=========================== private =========================================

/** 
 * Openmote-cc2538 AD4/DIO4 interrupt handler.
 * call the cb function specified.
 */
void openmote_GPIO_A_Handler(void) {
    //INTERRUPT_DECLARATION();

    // Disable interrupts 
    //DISABLE_INTERRUPTS();

    // clear the interrupt!
    GPIOPinIntClear(GPIO_A_BASE, GPIO_PIN_2); 

    llatency_send_pkt();

    //Enable interrupts 
    //ENABLE_INTERRUPTS();
}

/**
 *push task to scheduler with CoAP priority, and let scheduler take care of it.
*/
static void llatency_send_pkt(void){
   scheduler_push_task(llatency_task_cb,TASKPRIO_COAP);
   SCHEDULER_WAKEUP();
}

/**
 * 
 */
void llatency_task_cb() {
   //callback function called; toggle packet creation pin
   debugpins_pkt_toggle();

   OpenQueueEntry_t*    pkt;
   uint8_t              asnArray[5];
   uint32_t             values[2];
   
   // don't run if not synch
   if (ieee154e_isSynch() == FALSE) {
    //leds_debug_blink();
    return;
   } 
   
   // don't run on dagroot
   if (idmanager_getIsDAGroot()) {
      //opentimers_destroy(llatency_vars.timerId);
      return;
   }
  
   // if you get here, send a packet

   llatency_get_values(values);
   // get a free packet buffer
   pkt = openqueue_getFreePacketBuffer(COMPONENT_LLATENCY);
   if (pkt==NULL) {
      openserial_printError(
         COMPONENT_LLATENCY,
         ERR_NO_FREE_PACKET_BUFFER,
         (errorparameter_t)0,
         (errorparameter_t)0
      );
      return;
   }
   
   pkt->owner                         = COMPONENT_LLATENCY;
   pkt->creator                       = COMPONENT_LLATENCY;
   pkt->l4_protocol                   = IANA_UDP;
   pkt->l4_destination_port           = WKP_UDP_INJECT;
   pkt->l4_sourcePortORicmpv6Type     = WKP_UDP_INJECT;
   pkt->l3_destinationAdd.type        = ADDR_128B;
   memcpy(&pkt->l3_destinationAdd.addr_128b[0],llatency_dst_addr,16);
   
   // add payload
   packetfunctions_reserveHeaderSize(pkt,sizeof(llatency_payload)-1);
   memcpy(&pkt->payload[0],llatency_payload,sizeof(llatency_payload)-1);
   
   packetfunctions_reserveHeaderSize(pkt,sizeof(uint16_t));
   pkt->payload[1] = (uint8_t)((llatency_vars.counter & 0xff00)>>8);
   pkt->payload[0] = (uint8_t)(llatency_vars.counter & 0x00ff);
   llatency_vars.counter++;
   
   packetfunctions_reserveHeaderSize(pkt,sizeof(asn_t));

   ieee154e_getAsn(asnArray);
   pkt->payload[0] = asnArray[0];
   pkt->payload[1] = asnArray[1];
   pkt->payload[2] = asnArray[2];
   pkt->payload[3] = asnArray[3];
   pkt->payload[4] = asnArray[4];

   packetfunctions_reserveHeaderSize(pkt,sizeof(uint32_t));
   pkt->payload[3] = (uint8_t)((values[0] & 0xff000000)>>24);
   pkt->payload[2] = (uint8_t)((values[0] & 0x00ff0000)>>16);
   pkt->payload[1] = (uint8_t)((values[0] & 0x0000ff00)>>8);
   pkt->payload[0] = (uint8_t)(values[0] & 0x000000ff);

   packetfunctions_reserveHeaderSize(pkt,sizeof(uint32_t));
   pkt->payload[3] = (uint8_t)((values[1] & 0xff000000)>>24);
   pkt->payload[2] = (uint8_t)((values[1] & 0x00ff0000)>>16);
   pkt->payload[1] = (uint8_t)((values[1] & 0x0000ff00)>>8);
   pkt->payload[0] = (uint8_t)(values[1] & 0x000000ff);
   
   if ((openudp_send(pkt))==E_FAIL) {
      openqueue_freePacketBuffer(pkt);
   }
}



