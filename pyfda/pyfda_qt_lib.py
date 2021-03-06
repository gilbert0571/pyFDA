# -*- coding: utf-8 -*-
"""
Created 2012 - 2017

@author: Christian Muenker

Library with common routines for Qt widgets
"""

from __future__ import division, print_function
import logging
logger = logging.getLogger(__name__)

import csv
import io
import numpy as np
from .pyfda_lib import PY3
from .pyfda_rc import params 

from .compat import QFont, QEvent, QFrame

#------------------------------------------------------------------------------
def qstr(text):
    """
    Convert text (QVariant, QString, string) or numeric object to plain string.

    In Python 3, python Qt objects are automatically converted to QVariant
    when stored as "data" e.g. in a QComboBox and converted back when
    retrieving. In Python 2, QVariant is returned when itemData is retrieved.
    This is first converted from the QVariant container format to a
    QString, next to a "normal" non-unicode string.

    Parameter:
    ----------
    
    text: QVariant, QString, string or numeric data type that can be converted
      to string
    
    Returns:
    --------
    
    The current `text` data as a string
    """
    if "QString" in str(type(text)):
        # Python 3: convert QString -> str
        string = str(text)
#    elif not isinstance(text, six.text_type):
    elif "QVariant" in str(type(text)):
        # Python 2: convert QVariant -> QString -> str
        string = str(text.toString())
    else:
        # `text` is numeric or of type str
        string = str(text)
    return string


#------------------------------------------------------------------------------
def qget_cmb_box(cmb_box, data=True):
    """
    Get current itemData or Text of comboBox and convert it to string.

    In Python 3, python Qt objects are automatically converted to QVariant
    when stored as "data" e.g. in a QComboBox and converted back when
    retrieving. In Python 2, QVariant is returned when itemData is retrieved.
    This is first converted from the QVariant container format to a
    QString, next to a "normal" non-unicode string.

    Returns:
    
    The current text or data of combobox as a string
    """
    if data:
        idx = cmb_box.currentIndex()
        cmb_data = cmb_box.itemData(idx)
        cmb_str = qstr(cmb_data) # convert QVariant, QString, string to plain string
    else:
        cmb_str = cmb_box.currentText()
  
    cmb_str = str(cmb_str)

    return cmb_str

#------------------------------------------------------------------------------
def qset_cmb_box(cmb_box, string, data=False):
    """
    Set combobox to the index corresponding to `string` in a text field (data = False)
    or in a data field (data=True). When `string` is not found in the combobox entries,
     select the first entry. Signals are blocked during the update of the combobox.
     
    Returns: the index of the found entry
    """
    if data:
        idx = cmb_box.findData(str(string)) # find index for data = string
    else:
        idx = cmb_box.findText(str(string)) # find index for text = string    

    ret = idx

    if idx == -1: # data does not exist, use first entry instead
        idx = 0
        
    cmb_box.blockSignals(True)
    cmb_box.setCurrentIndex(idx) # set index
    cmb_box.blockSignals(False)
    
    return ret

#------------------------------------------------------------------------------
def qstyle_widget(widget, state):
    """
    Apply the "state" defined in pyfda_rc.py to the widget, e.g.:  
    Color the >> DESIGN FILTER << button according to the filter design state:
    
    - "normal": default, no color styling
    - "ok":  green, filter has been designed, everything ok
    - "changed": yellow, filter specs have been changed
    - "error" : red, an error has occurred during filter design
    - "failed" : orange, filter fails to meet target specs
    - "unused": grey
    """
    state = str(state)
    if state == 'u':
        state = "unused"
    elif state == 'a':
        state = "active"
    elif state == 'd':
        state = "disabled"
    widget.setProperty("state", state)
    #fb.design_filt_state = state
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()

#------------------------------------------------------------------------------
def qhline(widget):
    # http://stackoverflow.com/questions/5671354/how-to-programmatically-make-a-horizontal-line-in-qt
    # solution 
    """
    Create a horizontal line
    
    Parameters:
    
    frame: instance of QFrame - not needed?
    
    widget: widget containing the QFrame to be created
    """
    line = QFrame(widget)
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Sunken)
    return line
    
#------------------------------------------------------------------------------

def qget_selected(table, select_all=False, reverse=True):
    """
    Get selected cells in `table`and return a dictionary with the following keys:
    
    'idx': indices of selected cells as an unsorted list of tuples
    
    'sel': list of selected cells per column, by default sorted in reverse
    
    'cur':  current cell selection as a tuple

    Flags:

    'select_all' : select all table items and create a list

    'reverse' : return selected fields upside down
    """
    if select_all:
        table.selectAll()

    idx = []
    for _ in table.selectedItems():
        idx.append([_.column(), _.row(), ])

    sel = [0, 0]
    sel[0] = sorted([i[1] for i in idx if i[0] == 0], reverse = reverse)
    sel[1] = sorted([i[1] for i in idx if i[0] == 1], reverse = reverse)

    if select_all:
        table.clearSelection()

    # use set comprehension to eliminate multiple identical entries
    # cols = sorted(list({i[0] for i in idx}))
    # rows = sorted(list({i[1] for i in idx}))
    cur = (table.currentColumn(), table.currentRow())
    # cur_idx_row = table.currentIndex().row()
    return {'idx':idx, 'sel':sel, 'cur':cur}# 'rows':rows 'cols':cols, }
    

    
#------------------------------------------------------------------------------
def qcopy_to_clipboard(table, data, target, frmt):
    """
    Copy table to clipboard as CSV list
    
    Parameters:
    -----------
    table : object
            Instance of QTableWidget
            
    data:   object
            Instance of the variable containing table data
            
    target: object
            Target where the data is being copied to. If the object is a QClipboard
            instance, copy the text there, otherwise simply return the text.
            
    frmt: string
            Expected number format ('float', 'hex', ...)
    
    tab : String (default: "\t")
          Tabulator character for separating columns
          
    cr : String (default: CRLF, as determined by pyfda_lib)
            Line termination character for separating rows. When nothing is selected,
            the character is selected depending on the operating system:
            Windows: Carriage return + line feed
            MacOS  : Carriage return
            *nix   : Line feed
            
    orientation : Boolean
            When `vert` (default), generate the table in "vertical" shape,
            i.e. with one or two columns with coefficient data
    """

    text = ""
    if params['CSV']['header'] in {'auto', 'on'}:
        use_header = True
    elif params['CSV']['header'] == 'off':
        use_header = False
    else:
        logger.error("Unknown key '{0}' for params['CSV']['header']"
                                        .format(params['CSV']['header']))

    if params['CSV']['orientation'] in {'auto', 'vert'}:
        orientation_horiz = False
    elif params['CSV']['orientation'] == 'horiz':
        orientation_horiz = True
    else:
        logger.error("Unknown key '{0}' for params['CSV']['orientation']"
                                        .format(params['CSV']['orientation']))

    tab = params['CSV']['delimiter']
    cr = params['CSV']['lineterminator']

    num_cols = table.columnCount()
    num_rows = table.rowCount()

    sel = qget_selected(table, reverse=False)['sel']

    # when nothing is selected, select whole table for fixpoint (non-float) formats
    # otherwise, data would be copied from the raw data, not from the view (= table)    
    if not np.any(sel) and frmt != 'float':
        sel = qget_selected(table, reverse=False, select_all = True)['sel']

    #=======================================================================
    # Nothing selected, copy complete table
    #=======================================================================
    if not np.any(sel): 
        if orientation_horiz: # rows are horizontal
            for c in range(num_cols):
                if use_header: # add the table header
                    text += table.horizontalHeaderItem(c).text() + tab
                for r in range(num_rows):
                    text += str(data[c][r]) + tab
                text = text.rstrip(tab) + cr
            text = text.rstrip(cr) # delete last cr
        else:  # rows are vertical
            if use_header: # add the table header
                for c in range(num_cols):
                    text += table.horizontalHeaderItem(c).text() + tab
                text = text.rstrip(tab) + cr
            for r in range(num_rows):
                for c in range(num_cols):
                    text += str(data[c][r]) + tab
                text = text.rstrip(tab) + cr
            text = text.rstrip(cr) # delete CRLF after last row

    #=======================================================================
    # Copy only selected cells
    #=======================================================================
    else: # copy only selected cells in displayed format
        if orientation_horiz: # horizontal orientation, one or two rows
            print("sel:", np.shape(sel), sel)
            if use_header: # add the table header
                text += table.horizontalHeaderItem(0).text() + tab
            if sel[0]:
                for r in sel[0]:
                    item = table.item(r,0)
                    if item  and item.text() != "":
                            text += table.itemDelegate().text(item) + tab
                text = text.rstrip(tab) # remove last tab delimiter again

            if sel[1]: # returns False for []
                text += cr # add a CRLF when there are two columns
                if use_header: # add the table header
                    text += table.horizontalHeaderItem(1).text() + tab
                for r in sel[1]:
                    item = table.item(r,1)
                    if item and item.text() != "":
                            text += table.itemDelegate().text(item) + tab
                text = text.rstrip(tab) # remove last tab delimiter again
                print("horizontal\n", text)
        else: # vertical orientation, one or two columns
            sel_c = []
            if sel[0]:
                sel_c.append(0)
            if sel[1]:
                sel_c.append(1)

            if use_header:
                for c in sel_c:
                    text += table.horizontalHeaderItem(c).text() + tab
                    # cr is added further below
                text.rstrip(tab)
                
            for r in range(num_rows): # iterate over whole table
                for c in sel_c:
                    if r in sel[c]: # selected item?
                        item = table.item(r,c)
                        print(c,r)
                        if item and item.text() != "":
                            text += table.itemDelegate().text(item) + tab
                text = text.rstrip(tab) + cr
            text.rstrip(cr)

        print("qcopy_to_clipboard\n", text)

    if "clipboard" in str(target.__class__.__name__).lower():
        target.setText(text)
    else:
        return text

    # numpy.loadtxt  textfile -> array
    # numpy.savetxt array -> textfile
    # numpy.genfromtxt textfile -> array (with missing values)
    # numpy.recfromcsv
        
#==============================================================================
# http://stackoverflow.com/questions/6081008/dump-a-numpy-array-into-a-csv-file#6081043
#     # Write an example CSV file with headers on first line
#     with open('example.csv', 'w') as fp:
#         fp.write('''\
#     col1,col2,col3
#     1,100.1,string1
#     2,222.2,second string
#     ''')
#     
#     # Read it as a Numpy record array
#     ar = np.recfromcsv('example.csv')
#     print(repr(ar))
#     # rec.array([(1, 100.1, 'string1'), (2, 222.2, 'second string')], 
#     #           dtype=[('col1', '<i4'), ('col2', '<f8'), ('col3', 'S13')])
#     
#     # Write as a CSV file with headers on first line
#     with open('out.csv', 'w') as fp:
#         fp.write(','.join(ar.dtype.names) + '\n')
#         np.savetxt(fp, ar, '%s', ',')
#     
#     # Note that this example does not consider strings with commas, which would require quotes.
#         
#==============================================================================

#==============================================================================
#     # Here 'a' is the name of numpy array and 'file' is the variable to write in a file.
#     ##if you want to write in column:
# 
#     for x in np.nditer(a.T, order='C'): 
#             file.write(str(x))
#             file.write("\n")
# 
#     ## If you want to write in row: ## 
# 
#     writer= csv.writer(file, delimiter=',')
#     for x in np.nditer(a.T, order='C'): 
#             row.append(str(x))
#     writer.writerow(row)
# 
#==============================================================================
        
        
#------------------------------------------------------------------------------
def qcopy_from_clipboard(source):
    """
    Copy data from clipboard to table
    
    Parameters:
    -----------
            
    source: object
            Source of the data, this should be a QClipboard instance or an 
            opened file handle.
            
            If `source` is neither, return an error.
            
    The following keys from pyfda_lib.params['CSV'] are evaluated
                
    'delimiter' : string (default: <tab>)
          Character for separating columns
          
    'lineterminator' : string (default: As used by the operating system)
            Character for terminating rows. By default,
            the character is selected depending on the operating system:
            Windows: Carriage return + line feed
            MacOS  : Carriage return
            *nix   : Line feed
            
    'orientation' : string
            This string determines with which the orientation the table is read.
            
    'header ': string (default: 'auto')
            When `header='on'`, treat first row as a header that will be discarded.
        
    Parameters that are 'auto', will be guessed by csv.Sniffer().
            
    Returns:
    --------
            
    numpy array of strings
                containing table data
    """
    
    source_class = str(source.__class__.__name__).lower()
    # print(type(source))
    if "textiowrapper" in source_class or "bufferedreader" in source_class : #"_io.TextIOWrapper"
        # ^ Python 3 ('r' mode)            ^ Python 2 ('rb' mode)
        print("Using {0}".format(source))
        f = source # pass handle to opened file
    
    elif "clipboard" in source_class:
        # mime = source.mimeData()
        if PY3:
            text = source.text()
        else:
            text = unicode(source.text()) # Py 2 needs unicode here (why?)
        print(text, np.shape(text))
            
        f = io.StringIO(text) # pass handle to text

    else:
        logger.error("Unknown object {0}, cannot copy data.".format(source_class))
        raise IOError
        return None

#------------------------------------------------------------------------------
# Get CSV parameter settings
#------------------------------------------------------------------------------
    try:
        header = params['CSV']['header'].lower()       
        if header in {'auto', 'on', 'off'}:
            pass
        else:
            header = 'auto'
            logger.error("Unknown key '{0}' for params['CSV']['header'], using {1} instead."
                                            .format(params['CSV']['header']), header)

        orientation_horiz = params['CSV']['orientation'].lower()
        if orientation_horiz in {'auto', 'vert', 'horiz'}:
            pass
        else:
            orientation_horiz = 'vert'
            logger.error("Unknown key '{0}' for params['CSV']['orientation'], using {1} instead."
                                        .format(params['CSV']['orientation']), orientation_horiz)

        tab = params['CSV']['delimiter'].lower()
        cr = params['CSV']['lineterminator'].lower()

    except KeyError as e:
        logger.error(e)

    try:
        if header == 'auto' or tab == 'auto' or cr == 'auto':
        # test the first line for delimiters (of the given selection)
            dialect = csv.Sniffer().sniff(f.readline(), delimiters=['\t',';',',', '|', ' ']) 
            f.seek(0)                               # and reset the file pointer
        else:
            dialect = csv.get_dialect('excel-tab') # fall back, alternatives: 'excel', 'unix'

        if header == "auto":                                  
            use_header = csv.Sniffer().has_header(f.read(1000)) # True when header detected
            f.seek(0)  

    except csv.Error as e:
        logger.error("Error during CSV analysis:\n{0}".format(e)) 
        dialect = csv.get_dialect('excel-tab') # fall back
        use_header = False

    if header == 'on':
        use_header = True
    if header == 'off':
        use_header = False
    # case 'auto' has been treated above

    delimiter = dialect.delimiter
    lineterminator = dialect.lineterminator
    quotechar = dialect.quotechar

    if tab is not 'auto':
        delimiter = str(tab)
        
    if cr is not 'auto':
        lineterminator = str(cr)
        
    print("using delimiter:", repr(delimiter))
    print("using terminator:", repr(lineterminator))   
    print("using quotechar:", repr(quotechar))
    print("using header:", use_header)

    data_iter = csv.reader(f, dialect=dialect, delimiter=delimiter, lineterminator=lineterminator) # returns an iterator
    # f.seek(0) 
    if use_header:
        print("headers: ", next(data_iter, None)) # py3 and py2 
    
    data_list = []
    for row in data_iter:
        print(row)
        data_list.append(row)

    try:
        print(type(data_list))
        data_arr = np.array(data_list)
        cols, rows = np.shape(data_arr)
        print("cols = {0}, rows = {1}, data_arr = \n".format(cols, rows, data_arr))
        if params['CSV']['orientation'] == 'vert':
            print(data_arr.T)
            return data_arr.T
        else:
            print(data_arr)
            return data_arr
            
    except (TypeError, ValueError) as e:
        logger.error("{0}\n{1}".format(e, data_list))
        return None


#==============================================================================

if __name__=='__main__':
    pass
