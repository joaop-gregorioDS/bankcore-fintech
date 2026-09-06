// Mock catalog matching iOS MockCatalog.swift
export function getMockCatalog(taxId) {
  const digits = String(taxId || '').replace(/\D/g, '');
  const isLucas = digits === '98765432100';
  const isMaria = digits === '12345678900';

  if (isLucas) {
    return {
      segment: 'Vortex Carbon Black Corporate',
      badge: 'PJ / Carbon Black',
      agency: '0001-9',
      accountNumber: '77412-7',
      pixLimitReais: 50000,
      scheduledTotalReais: 3069.40,
      cards: [
        {
          id: 'card-1',
          name: 'Carbon Black',
          type: 'physical',
          brand: 'Mastercard Black',
          last4: '4289',
          holder: 'LUCAS MENDES',
          invoice: 2296.07,
          used: 8371.00,
          available: 12260.00,
          total: 20631.00,
          dueDate: '10 de Setembro',
          period: '30/Jul a 31/Ago',
          isVirtual: false,
        },
        {
          id: 'card-2',
          name: 'Carbon Virtual',
          type: 'virtual',
          brand: 'Visa Infinite',
          last4: '7712',
          holder: 'LUCAS MENDES',
          invoice: 412.90,
          used: 412.90,
          available: 4587.10,
          total: 5000.00,
          dueDate: '10 de Setembro',
          period: 'Fatura virtual',
          isVirtual: true,
        },
      ],
      dda: [
        { id: 'dda-1', company: 'AWS Cloud Services', due: '12/Set', amount: 1840.50, barcode: '34191.79001 01043.510047 91020.150008 8 98450000184050' },
        { id: 'dda-2', company: 'Contabilizei Serviços Contábeis', due: '15/Set', amount: 429.90, barcode: '03399.63820 12345.678901 23456.789012 3 98480000042990' },
        { id: 'dda-3', company: 'Vivo Fibra Empresas Dedicada', due: '18/Set', amount: 389.00, barcode: '23793.38128 60000.123456 78901.234567 1 98510000038900' },
        { id: 'dda-4', company: 'Google Workspace Brasil', due: '20/Set', amount: 240.00, barcode: '34191.79001 01043.510047 91020.150008 8 98530000024000' },
        { id: 'dda-5', company: 'Serasa Experian PJ', due: '25/Set', amount: 170.00, barcode: '03399.63820 12345.678901 23456.789012 3 98580000017000' },
      ],
      investments: {
        totalReais: 23750.00,
        monthlyYield: '+1,12%',
        items: [
          { name: 'CDB Carbon Liquidez Diária (108% CDI)', value: 15000.00, institution: 'Banco Vortex', maturity: 'D+0' },
          { name: 'LCI Vortex Verde Sustentável (94% CDI Isento)', value: 8750.00, institution: 'Vortex DTVM', maturity: '24 meses' },
        ],
      },
      credit: {
        preApprovedReais: 50000.00,
        monthlyRate: '1,49% a.m.',
        maxMonths: 48,
        usedReais: 0,
      },
    };
  }

  // Default / Maria
  return {
    segment: isMaria ? 'Vortex Carbon Platinum' : 'Correntista BankCore',
    badge: isMaria ? 'PF / Carbon Platinum' : 'Demo Standard',
    agency: '0001-9',
    accountNumber: isMaria ? '88921-3' : '10001-2',
    pixLimitReais: 35000,
    scheduledTotalReais: 1985.20,
    cards: [
      {
        id: 'card-1',
        name: 'Carbon Platinum',
        type: 'physical',
        brand: 'Mastercard Platinum',
        last4: '8821',
        holder: isMaria ? 'MARIA SILVA' : 'CORRENTISTA',
        invoice: 1480.30,
        used: 4210.00,
        available: 15790.00,
        total: 20000.00,
        dueDate: '10 de Setembro',
        period: '30/Jul a 31/Ago',
        isVirtual: false,
      },
    ],
    dda: [
      { id: 'dda-1', company: 'Condomínio Edifício Solar', due: '10/Set', amount: 890.00, barcode: '23793.38128 60000.123456 78901.234567 1 98430000089000' },
      { id: 'dda-2', company: 'Unimed Saúde Nacional', due: '14/Set', amount: 740.00, barcode: '34191.79001 01043.510047 91020.150008 8 98470000074000' },
      { id: 'dda-3', company: 'Enel Distribuição SP', due: '17/Set', amount: 195.30, barcode: '03399.63820 12345.678901 23456.789012 3 98500000019530' },
      { id: 'dda-4', company: 'Claro Fibra + Móvel 5G', due: '22/Set', amount: 159.90, barcode: '34191.79001 01043.510047 91020.150008 8 98550000015990' },
    ],
    investments: {
      totalReais: 14500.00,
      monthlyYield: '+1,05%',
      items: [
        { name: 'CDB Vortex 100% CDI', value: 10000.00, institution: 'Banco Vortex', maturity: 'D+0' },
        { name: 'Tesouro Direto Selic 2029', value: 4500.00, institution: 'Tesouro Nacional', maturity: '2029' },
      ],
    },
    credit: {
      preApprovedReais: 35000.00,
      monthlyRate: '1,59% a.m.',
      maxMonths: 36,
      usedReais: 0,
    },
  };
}
