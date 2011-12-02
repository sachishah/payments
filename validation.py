__author__ = 'sshah'
'''

class ValidationFormulas:

    def isBankRoutingNumber(self,bankNumber):
        """Parses the bank routing number for purposes of finding a fraudulent entry.
            the algorithm check the first second and third number and adds them together,
            then iterates through every three numbers (total of 9) to return a value.

           If the resulting sum is an even multiple of ten (but not zero), the ABA
            routing number is good.

           param -- bankNumber the 9 digit bank number;

           return boolean true if number is valid, false if not. false is the default
           """
        n=0
        retbool=False
        bank_str = str(bankNumber)
        num_length = len(bank_str)
        if (num_length ==9):
            for j in range(0,num_length,3):
                t = int(bank_str[j])
                ti = int(bank_str[j + 1])
                tii = int(bank_str[j + 2])
                n += (t * 3)+ (ti * 7)+ tii
            retbool = (n != 0) & ((n % 10) == 0)
        #return the value
        return retbool
'''