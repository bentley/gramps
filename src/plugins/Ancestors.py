#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2003  Donald N. Allingham
# Copyright (C) 2003  Tim Waugh
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

# $Id$

import gtk

#------------------------------------------------------------------------
#
# gramps modules
#
#------------------------------------------------------------------------
import Report
import TextDoc
import RelLib
import Errors
from QuestionDialog import ErrorDialog
from intl import gettext as _

#------------------------------------------------------------------------
#
# ComprehensiveAncestorsReport
#
#------------------------------------------------------------------------
class ComprehensiveAncestorsReport (Report.Report):

    def __init__(self,database,person,max,pgbrk,cite,doc,output,newpage=0):
        self.map = {}
        self.database = database
        self.start = person
        self.max_generations = max
        self.pgbrk = pgbrk
        self.opt_cite = cite
        self.doc = doc
        self.sources = []
        self.sourcerefs = []
        self.newpage = newpage

        table = TextDoc.TableStyle ()
        table.set_column_widths ([15, 85])
        table.set_width (100)
        doc.add_table_style ("AR-PersonNoSpouse", table)

        table = TextDoc.TableStyle ()
        table.set_column_widths ([10, 15, 75])
        table.set_width (100)
        doc.add_table_style ("AR-ChildNoSpouse", table)

        for nspouse in range (1, 3):
            table = TextDoc.TableStyle ()
            table.set_width (100)
            widths = [15, 100 - 15 * (nspouse + 1)]
            widths.extend ([15] * nspouse)
            table.set_column_widths (widths)
            doc.add_table_style ("AR-PersonWithSpouse%d" % nspouse, table)

            table = TextDoc.TableStyle ()
            table.set_width (100)
            widths = [10, 15, 90 - 15 * (nspouse + 1)]
            widths.extend ([15] * nspouse)
            table.set_column_widths (widths)
            doc.add_table_style ("AR-ChildWithSpouse%d"% nspouse, table)

        cell = TextDoc.TableCellStyle ()
        cell.set_padding (1) # each side makes 2cm, the size of the photo
        doc.add_cell_style ("AR-PaddedCell", cell)

        cell = TextDoc.TableCellStyle ()
        cell.set_padding (0.1)
        cell.set_left_border (1)
        cell.set_top_border (1)
        cell.set_right_border (1)
        cell.set_bottom_border (1)
        doc.add_cell_style ("AR-NoPhoto", cell)

        cell = TextDoc.TableCellStyle ()
        cell.set_padding (0.1)
        doc.add_cell_style ("AR-Photo", cell)

        cell = TextDoc.TableCellStyle ()
        cell.set_padding (0.1)
        doc.add_cell_style ("AR-Entry", cell)

        if output:
            self.standalone = 1
            self.doc.open(output)
        else:
            self.standalone = 0

    def write_report(self):
        if self.newpage:
            self.doc.page_break()

        self.sources = []
        name = self.person_name (self.start)
        self.doc.start_paragraph("AR-Title")
        title = _("Ancestors of %s") % name
        self.doc.write_text(title)
        self.doc.end_paragraph()

        self.doc.start_paragraph ("AR-Heading")
        self.doc.write_text ("Generation 1")
        self.doc.end_paragraph ()

        self.write_paragraphs (self.person (self.start, suppress_children = 1,
                                            needs_name = 1))
        families = [self.start.getMainParents ()]
        if len (families) > 0:
            self.generation (self.max_generations, families, [self.start])

        if len (self.sources) > 0:
            self.doc.start_paragraph ("AR-Heading")
            self.doc.write_text ("Sources")
            self.doc.end_paragraph ()

            i = 1
            for source in self.sources:
                self.doc.start_paragraph ("AR-Entry")
                self.doc.write_text ("[%d] %s" % (i, source.getTitle ()))
                self.doc.end_paragraph ()

                note = source.getNote ()
                if note:
                    self.doc.start_paragraph ("AR-Details")
                    self.doc.write_text (note)
                    self.doc.end_paragraph ()

                i += 1

        if self.standalone:
            self.doc.close()
        return

    def write_paragraphs (self, paragraphs):
        for (fn, params) in paragraphs:
            if len (params) == 0:
                fn ()
            elif len (params) == 1:
                fn (params[0])
            elif len (params) == 2:
                fn (params[0], params[1])
            elif len (params) == 3:
                fn (params[0], params[1], params[2])
            elif len (params) == 4:
                fn (params[0], params[1], params[2], params[3])
            else:
                self.doc.write_text ("Call to %s with params %s" %
                                     (str (fn), str (params)))

    def family (self, family, already_described):
        ret = []
        if not family:
            return ret
        father = family.getFather ()
        mother = family.getMother ()
        if father:
            ret.extend (self.person (father,
                                     short_form = father in already_described,
                                     already_described = already_described,
                                     needs_name = not mother,
                                     from_family = family))

        if mother:
            ret.extend (self.person (mother,
                                     short_form = mother in already_described,
                                     already_described = already_described,
                                     needs_name = not father,
                                     from_family = family))

        children = family.getChildList ()
        if len (children):
            ret.append ((self.doc.start_paragraph, ['AR-ChildTitle']))
            ret.append ((self.doc.write_text, ['Their children:']))
            ret.append ((self.doc.end_paragraph, []))

            for child in children:
                ret.extend (self.person (child, suppress_children = 1,
                                         short_form=child in already_described,
                                         already_described = already_described,
                                         needs_name = 1,
                                         from_family = family))

        return ret

    def generation (self, generations, families, already_described,
                    thisgen = 2):
        if generations > 1 and len (families):
            people = []
            for family in families:
                people.extend (self.family (family, already_described))

            if len (people):
                if self.pgbrk:
                    self.doc.page_break()
                self.doc.start_paragraph ("AR-Heading")
                if thisgen > 4:
                    n = thisgen - 3
                    if n % 10 == 1 and n != 11:
                        nth = 'st'
                    elif n % 10 == 2 and n != 12:
                        nth = 'nd'
                    elif n % 10 == 3 and n != 13:
                        nth = 'rd'
                    else:
                        nth = 'th'
                    heading = '%d%s great grandparents' % (n, nth)
                elif thisgen == 4:
                    heading = 'Great grandparents'
                elif thisgen == 3:
                    heading = 'Grandparents'
                elif thisgen == 2:
                    heading = 'Parents'
                else:
                    heading = 'Generation %d' % thisgen
                self.doc.write_text (heading)
                self.doc.end_paragraph ()
                self.write_paragraphs (people)

                next_families = []
                for family in families:
                    father = family.getFather ()
                    if father:
                        already_described.append (father)
                        father_family = father.getMainParents ()
                        if father_family:
                            next_families.append (father_family)

                    mother = family.getMother ()
                    if mother:
                        already_described.append (mother)
                        mother_family = mother.getMainParents ()
                        if mother_family:
                            next_families.append (mother_family)

                self.generation (generations - 1, next_families,
                                 already_described, thisgen + 1)

    def person (self, person,
                suppress_children = 0,
                short_form = 0,
                already_described = [],
                needs_name = 0,
                from_family = None):
        ret = []
        name = self.person_name (person)
        if name:
            photos = person.getPhotoList ()

            bits = ''
            bits += self.short_occupation (person)
            bits += self.long_born_died (person)
            if not suppress_children:
                bits += self.parents_of (person)
            else:
                bits += '.'
            bits += self.married_whom (person, from_family, suppress_children)
            bits += self.inline_notes (person)

            longnotes = self.long_notes (person, suppress_children,
                                         already_described)

            if (bits != '.' or longnotes or photos or
                suppress_children or needs_name):
                # We have something to say about this person.

                spouse = []
                if from_family:
                    from_family_father = from_family.getFather ()
                    from_family_mother = from_family.getMother ()
                else:
                    from_family_father = from_family_mother = None

                for family in person.getFamilyList ():
                    for partner in [family.getFather (),
                                    family.getMother ()]:
                        if partner == person or not partner:
                            continue

                        if (suppress_children or
                            (partner != from_family_father and
                             partner != from_family_mother)):
                            for photo in partner.getPhotoList ()[:1]:
                                spouse.append ((self.doc.add_photo,
                                                [photo.ref.getPath (),
                                                 'right', 2, 2]))

                if suppress_children and len (already_described):
                    style = "AR-Child"
                else:
                    style = "AR-Person"
                if len (spouse):
                    style += "WithSpouse%d" % len (spouse)
                else:
                    style += "NoSpouse"

                ret.append ((self.doc.start_table, [style, style]))
                ret.append ((self.doc.start_row, []))

                if suppress_children and len (already_described):
                    # Can't do proper formatting with TextDoc, so cheat.
                    ret.append ((self.doc.start_cell, ["AR-PaddedCell"]))
                    ret.append ((self.doc.end_cell, []))

                if len (photos) == 0:
                    ret.append ((self.doc.start_cell, ["AR-NoPhoto"]))
                    ret.append ((self.doc.start_paragraph, ["AR-NoPhotoText"]))
                    ret.append ((self.doc.write_text, ["(no photo)"]))
                    ret.append ((self.doc.end_paragraph, []))
                    ret.append ((self.doc.end_cell, []))
                else:
                    ret.append ((self.doc.start_cell, ["AR-Photo"]))
                    for photo in photos[:1]:
                        ret.append ((self.doc.add_photo,
                                     [photo.ref.getPath (), 'left', 2, 2]))
                        ret.append ((self.doc.end_cell, []))

                ret.append ((self.doc.start_cell, ["AR-Entry"]))
                ret.append ((self.doc.start_paragraph, ["AR-Entry"]))
                ret.append ((self.doc.write_text, [name]))
                if short_form:
                    ret.append ((self.doc.write_text, [" (mentioned above)."]))
                else:
                    ret.append ((self.doc.write_text, [bits]))

                ret.append ((self.doc.end_paragraph, []))
                ret.append ((self.doc.end_cell, []))

                for s in spouse:
                    ret.append ((self.doc.start_cell, ["AR-Photo"]))
                    ret.append (s)
                    ret.append ((self.doc.end_cell, []))

                ret.append ((self.doc.end_row, []))
                ret.append ((self.doc.end_table, []))

                if not short_form:
                    ret.extend (longnotes)

        return ret

    def short_occupation (self, person):
        occupation = ''
        for event in person.getEventList ():
            if event.getName () == 'Occupation':
                if occupation:
                    return ''

                occupation = event.getDescription ()

        if occupation:
            return ' (%s)' % occupation

        return ''

    def event_info (self, event):
        info = ''
        name = event.getName ()
        description = event.getDescription ()
        if name != 'Birth' and name != 'Death' and name != 'Marriage':
            info += name
            if description:
                info += ': ' + description
                description = None

        dateobj = event.getDateObj ()
        if dateobj:
            text = dateobj.getText ()
            if text:
                info += ' ' + text[0].lower() + text[1:]
            elif dateobj.getValid ():
                if dateobj.isRange ():
                    info += ' '
                elif (dateobj.getDayValid () and
                    dateobj.getMonthValid () and
                    dateobj.getYearValid ()):
                    info += ' on '
                else:
                    info += ' in '

                info += dateobj.getDate ()
        placename = event.getPlaceName ()
        if placename:
            info += ' in ' + placename
        note = event.getNote ()
        if note or description:
            info += ' ('
            if description:
                info += description
            if note:
                if description:
                    info += '; '
                info += note
            info += ')'

        info += self.cite_sources (event.getSourceRefList ())
        return info

    def address_info (self, address):
        info = 'Address: %s %s %s %s' % (address.getStreet (),
                                         address.getCity (),
                                         address.getState (),
                                         address.getCountry ())

        info = info.rstrip ()
        date = address.getDate ()
        if date:
            info += ', ' + date

        info += self.cite_sources (address.getSourceRefList ())
        return info

    def abbrev_born_died (self, person):
        ret = ''
        birth = person.getBirth ()
        date = birth.getDate ()
        if date:
            ret += " b. " + date
            ret += self.cite_sources (birth.getSourceRefList ())

        death = person.getDeath ()
        date = death.getDate ()
        if date:
            ret += " d. " + date
            ret += self.cite_sources (death.getSourceRefList ())

        return ret

    def long_born_died (self, person):
        ret = ''
        born_info = self.event_info (person.getBirth ())
        if born_info:
            ret = ", born" + born_info

        died_info = self.event_info (person.getDeath ())
        if died_info:
            if born_info:
                ret += '; '
            else:
                ret += ', '

            ret += 'died' + died_info

        return ret

    def Pronoun (self, person):
        if person.getGender () == RelLib.Person.female:
            return 'She'
        else:
            return 'He'

    def son_or_daughter (self, person):
        if person.getGender () == RelLib.Person.female:
            return 'daughter'
        else:
            return 'son'

    def parents_of (self, person):
        childof = ('.  ' + self.Pronoun (person) + ' is the ' +
                   self.son_or_daughter (person) + ' of ')
        family = person.getMainParents ()
        ret = ''
        if family:
            fathername = mothername = None
            father = family.getFather ()
            if father:
                fathername = self.person_name (father)
            mother = family.getMother ()
            if mother:
                mothername = self.person_name (mother)

            if not mother and not father:
                pass
            elif not father:
                ret = childof + mothername
            elif not mother:
                ret = childof + fathername
            else:
                ret = childof + fathername + ' and ' + mothername

        return ret + '.'

    def first_name_or_nick (self, person):
        nickname = person.getNickName ()
        if nickname:
            return nickname

        name = person.getPrimaryName ().getFirstName ()
        return name.split (' ')[0]

    def title (self, person):
        name = person.getPrimaryName ()
        t = name.getTitle ()
        if t:
            return t

        gender = person.getGender ()
        if gender == RelLib.Person.female:
            if name.getType () == 'Married Name':
                return 'Mrs.'

            return 'Miss'
        elif gender == RelLib.Person.male:
            return 'Mr.'
        else:
            return '(gender unknown)'

    def cite_sources (self, sourcereflist):
        citation = ""
        if self.opt_cite:
            for ref in sourcereflist:
                if ref in self.sourcerefs:
                    continue

                self.sourcerefs.append (ref)
                source = ref.getBase ()
                if source in self.sources:
                    ind = self.sources.index (source) + 1
                else:
                    self.sources.append (source)
                    ind = len (self.sources)

                citation += "[%d" % ind
                comments = ref.getComments ()
                if comments and comments.find ('\n') == -1:
                    citation += " - %s" % comments.rstrip ('.')

                citation += "]"

        return citation

    def person_name (self, person):
        primary = person.getPrimaryName ()

        name = primary.getTitle ()
        if name:
            name += ' '

        first = primary.getFirstName ()
        last = primary.getSurname ()
        first_replaced = first.replace ('?', '')
        if first_replaced == '':
            name += self.title (person)
        else:
            name += first

        nick = person.getNickName ()
        if nick:
            nick.strip ('"')
            name += ' ("%s")' % nick

        if last.replace ('?', '') == '':
            if first_replaced == '':
                name += ' (unknown)'
        else:
            name += ' ' + last

        suffix = primary.getSuffix ()
        if suffix:
            name += ', ' + suffix

        type = primary.getType ()
        if type != 'Birth Name':
            name += ' (%s)' % type

        name += self.cite_sources (primary.getSourceRefList ())
        return name

    def married_whom (self, person, from_family, listing_children = 0):
        pronoun = '  ' + self.Pronoun (person)
        first_marriage = 1
        ret = ''
        for family in person.getFamilyList ():
            mother = family.getMother ()
            for spouse in [family.getFather (), mother]:
                if spouse == person or not spouse:
                    continue

                children = ''
                childlist = family.getChildList ()
                child_count = len (childlist)
                if ((listing_children or family != from_family) and
                    child_count > 0):
                    children = ', and they had '
                    if child_count == 1:
                        children += 'a child named '
                    else:
                        children += str (child_count) + ' children: '

                    count = 1
                    for child in childlist:
                        children += self.first_name_or_nick (child)
                        children += self.cite_sources (child.getPrimaryName ().
                                                       getSourceRefList ())
                        children += self.abbrev_born_died (child)
                        if child_count - count > 1:
                            children += ', '
                        elif child_count - count == 1:
                            children += ' and '

                        count += 1

                marriage = family.getMarriage ()
                if not first_marriage:
                    ret += pronoun + ' later married '
                    ret += self.person_name (spouse)
                    if marriage:
                        ret += self.event_info (marriage)
                    ret += children + '.'
                elif (listing_children or
                      spouse == mother or
                      family != from_family):
                    ret += pronoun + ' married '
                    ret += self.person_name (spouse)
                    if marriage:
                        ret += self.event_info (marriage)
                    ret += children + '.'

            first_marriage = 0

        return ret

    def inline_notes (self, person):
        name_note = person.getPrimaryName ().getNote ()
        if not (name_note == '' or name_note.find ('\n') != -1):
            return '  Note about their name: ' + name_note
        note = person.getNote ()
        if not (note == '' or note.find ('\n') != -1):
            return '  ' + note

        return ''

    def long_details (self, note, paras):
        para_end = note.find ('\n')
        if para_end != -1:
            paras = self.long_details (note[note.find ('\n') + 1:], paras)
	else:
            para_end = len (note)

        paras.insert (0, (self.doc.end_paragraph, []))
        paras.insert (0, (self.doc.write_text, [note[:para_end]]))
        paras.insert (0, (self.doc.start_paragraph, ['AR-Details']))
        return paras

    def long_notes (self, person, suppress_children = 0,
                    already_described = []):
        note = person.getNote ()
        if note != '' and note.find ('\n') != -1:
            paras = self.long_details (note, [])
        else:
            paras = []

        names = person.getAlternateNames ()
        events = person.getEventList ()
        addresses = person.getAddressList ()
        if (len (events) + len (addresses) + len (names)) > 0:
            paras.append ((self.doc.start_paragraph, ['AR-SubEntry']))
            paras.append ((self.doc.write_text,
                           ["More about " +
                            self.first_name_or_nick (person) +
                            ":"]))
            paras.append ((self.doc.end_paragraph, []))

        for name in names:
            paras.append ((self.doc.start_paragraph, ['AR-Details']))
            paras.append ((self.doc.write_text, [name.getType () + ': ' +
                                                 name.getRegularName ()]))
            paras.append ((self.doc.end_paragraph, []))

        for event in events:
            paras.append ((self.doc.start_paragraph, ['AR-Details']))
            paras.append ((self.doc.write_text, [self.event_info (event)]))
            paras.append ((self.doc.end_paragraph, []))

        for address in addresses:
            paras.append ((self.doc.start_paragraph, ['AR-Details']))
            paras.append ((self.doc.write_text, [self.address_info (address)]))
            paras.append ((self.doc.end_paragraph, []))

        return paras

def _make_default_style(default_style):
    """Make the default output style for the Comprehensive Ancestors report."""
    font = TextDoc.FontStyle()
    font.set(face=TextDoc.FONT_SANS_SERIF,size=16,bold=1,italic=1)
    para = TextDoc.ParagraphStyle()
    para.set_font(font)
    para.set_header_level(1)
    para.set_alignment(TextDoc.PARA_ALIGN_CENTER)
    para.set(pad=0.5)
    para.set_description(_('The style used for the title of the page.'))
    default_style.add_style("AR-Title",para)
    
    font = TextDoc.FontStyle()
    font.set(face=TextDoc.FONT_SANS_SERIF,size=14,italic=1)
    para = TextDoc.ParagraphStyle()
    para.set_font(font)
    para.set_header_level(2)
    para.set(pad=0.5)
    para.set_alignment(TextDoc.PARA_ALIGN_CENTER)
    para.set_description(_('The style used for the generation header.'))
    default_style.add_style("AR-Heading",para)

    para = TextDoc.ParagraphStyle()
    para.set(lmargin=1.0,pad=0.25)
    para.set_description(_('The basic style used for the text display.'))
    default_style.add_style("AR-Entry",para)

    para = TextDoc.ParagraphStyle ()
    para.set_description(_('Text style for missing photo.'))
    default_style.add_style("AR-NoPhotoText", para)

    details_font = TextDoc.FontStyle()
    details_font.set(face=TextDoc.FONT_SANS_SERIF,size=8,italic=1)
    para = TextDoc.ParagraphStyle()
    para.set(lmargin=2.7,pad=0,font = details_font)
    para.set_description(_('Style for details about a person.'))
    default_style.add_style("AR-Details",para)

    para = TextDoc.ParagraphStyle()
    para.set(lmargin=2.5,pad=0.25)
    para.set_description(_('The basic style used for the text display.'))
    para.set_header_level (4)
    default_style.add_style("AR-SubEntry",para)

    para = TextDoc.ParagraphStyle()
    para.set(pad=0.05)
    para.set_description(_('The basic style used for the text display.'))
    default_style.add_style("AR-Endnotes",para)

    para = TextDoc.ParagraphStyle()
    para.set(lmargin=1.0,pad=0.05)
    para.set_description(_('Introduction to the children.'))
    para.set_header_level (3)
    default_style.add_style("AR-ChildTitle",para)


#------------------------------------------------------------------------
#
# 
#
#------------------------------------------------------------------------
class ComprehensiveAncestorsReportDialog(Report.TextReportDialog):
    def __init__(self,database,person):
        Report.TextReportDialog.__init__(self,database,person)

    #------------------------------------------------------------------------
    #
    # Customization hooks
    #
    #------------------------------------------------------------------------
    def doc_uses_tables (self):
        return 1

    def get_title(self):
        """The window title for this dialog"""
        return "%s - %s - GRAMPS" % (_("Comprehensive Ancestors Report"),
                                     _("Text Reports"))

    def get_header(self, name):
        """The header line at the top of the dialog contents"""
        return _("Ancestors for %s") % name

    def get_target_browser_title(self):
        """The title of the window created when the 'browse' button is
        clicked in the 'Save As' frame."""
        return _("Save Ancestor Report")

    def get_stylesheet_savefile(self):
        """Where to save styles for this report."""
        return "ancestors_report.xml"
    
    def make_default_style(self):
        _make_default_style(self.default_style)

    def add_user_options (self):
        self.cb_cite = gtk.CheckButton (_("Cite sources"))
        self.cb_cite.set_active (gtk.TRUE)
        self.add_option ('', self.cb_cite)

    def parse_report_options_frame (self):
        # Call base class
        Report.ReportDialog.parse_report_options_frame (self)
        self.opt_cite = self.cb_cite.get_active ()

    def make_report(self):

        """Create the object that will produce the Comprehensive
        Ancestors Report.  All user dialog has already been handled
        and the output file opened."""
        try:
            MyReport = ComprehensiveAncestorsReport(self.db, self.person,
                                                    self.max_gen, self.pg_brk,
                                                    self.opt_cite, self.doc,
                                                    self.target_path)
            MyReport.write_report()
        except Errors.ReportError, msg:
            (m1,m2) = msg.messages()
            ErrorDialog(m1,m2)
        except Errors.FilterError, msg:
            (m1,m2) = msg.messages()
            ErrorDialog(m1,m2)
        except:
            import DisplayTrace
            DisplayTrace.DisplayTrace()

#------------------------------------------------------------------------
#
# Standalone report function
#
#------------------------------------------------------------------------
def report(database,person):
    ComprehensiveAncestorsReportDialog(database,person)

#------------------------------------------------------------------------
#
# Set up sane defaults for the book_item
#
#------------------------------------------------------------------------
_style_file = "ancestors_report.xml"
_style_name = "default" 

_person_id = ""
_max_gen = 10
_pg_brk = 0
_opt_cite = gtk.TRUE

_options = ( _person_id, _max_gen, _pg_brk, _opt_cite )

#------------------------------------------------------------------------
#
# Book Item Options dialog
#
#------------------------------------------------------------------------
class ComprehensiveAncestorsBareReportDialog(Report.BareReportDialog):

    def __init__(self,database,person,opt,stl):

        self.options = opt
        self.db = database
        if self.options[0]:
            self.person = self.db.getPerson(self.options[0])
        else:
            self.person = person
        self.style_name = stl

        Report.BareReportDialog.__init__(self,database,self.person)

        self.max_gen = int(self.options[1]) 
        self.pg_brk = int(self.options[2])
        self.opt_cite = int(self.options[3])
        self.new_person = None

        self.generations_spinbox.set_value(self.max_gen)
        self.pagebreak_checkbox.set_active(self.pg_brk)
        self.cb_cite.set_active(self.opt_cite)

        self.window.run()

    #------------------------------------------------------------------------
    #
    # Customization hooks
    #
    #------------------------------------------------------------------------
    def make_default_style(self):
        _make_default_style(self.default_style)

    def get_title(self):
        """The window title for this dialog"""
        return "%s - GRAMPS Book" % (_("Comprehensive Ancestors Report"))

    def get_header(self, name):
        """The header line at the top of the dialog contents"""
        return _("Comprehensive Ancestors Report for GRAMPS Book") 

    def get_stylesheet_savefile(self):
        """Where to save styles for this report."""
        return _style_file
    
    def add_user_options (self):
        self.cb_cite = gtk.CheckButton (_("Cite sources"))
        self.add_option ('', self.cb_cite)

    def parse_report_options_frame (self):
        # Call base class
        Report.BareReportDialog.parse_report_options_frame (self)
        self.opt_cite = self.cb_cite.get_active ()

    def on_cancel(self, obj):
        pass

    def on_ok_clicked(self, obj):
        """The user is satisfied with the dialog choices. Parse all options
        and close the window."""

        # Preparation
        self.parse_style_frame()
        self.parse_report_options_frame()
        
        if self.new_person:
            self.person = self.new_person
        self.options = ( self.person.getId(), self.max_gen, self.pg_brk, self.opt_cite )
        self.style_name = self.selected_style.get_name() 

#------------------------------------------------------------------------
#
# Function to write Book Item 
#
#------------------------------------------------------------------------
def write_book_item(database,person,doc,options,newpage=0):
    """Write the Comprehensive Ancestors Report using options set.
    All user dialog has already been handled and the output file opened."""
    try:
        if options[0]:
            person = database.getPerson(options[0])
        max_gen = int(options[1])
        pg_brk = int(options[2])
        opt_cite = int(options[3])
        return ComprehensiveAncestorsReport(database, person,
            max_gen, pg_brk, opt_cite, doc, None, newpage)
    except Errors.ReportError, msg:
        (m1,m2) = msg.messages()
        ErrorDialog(m1,m2)
    except Errors.FilterError, msg:
        (m1,m2) = msg.messages()
        ErrorDialog(m1,m2)
    except:
        import DisplayTrace
        DisplayTrace.DisplayTrace()

#------------------------------------------------------------------------
#
# 
#
#------------------------------------------------------------------------
def get_xpm_image():
    return [
        "48 48 33 1",
        " 	c None",
        ".	c #1A1A1A",
        "+	c #847B6E",
        "@	c #B7AC9C",
        "#	c #D1D1D0",
        "$	c #EEE2D0",
        "%	c #6A655C",
        "&	c #868686",
        "*	c #F1EADF",
        "=	c #5C5854",
        "-	c #B89C73",
        ";	c #E2C8A1",
        ">	c #55524C",
        ",	c #F5EEE6",
        "'	c #4F4E4C",
        ")	c #A19C95",
        "!	c #B3966E",
        "~	c #CDC8BF",
        "{	c #F6F2ED",
        "]	c #A6A5A4",
        "^	c #413F3F",
        "/	c #D8D1C5",
        "(	c #968977",
        "_	c #BAB9B6",
        ":	c #FAFAF9",
        "<	c #BEA27B",
        "[	c #E9DAC2",
        "}	c #9D9385",
        "|	c #E4E3E3",
        "1	c #7A7062",
        "2	c #E6D3B4",
        "3	c #BAA488",
        "4	c #322E2B",
        "                                                ",
        "                                                ",
        "             (+(+++++111%1%%%%===%1             ",
        "             +______________@_@)&==1            ",
        "             +_::::::::::::::*|#_&&}>           ",
        "             &_:::::::::::::::{|#]1~}^          ",
        "             +_::::::::::::::::{|#=|~&4         ",
        "             +_::::]]]]]]]]:::::|{':|~&4        ",
        "             +_::::::::::::::::::{'::|~&4       ",
        "             +_:::::::::::::::::::'*::|~&^      ",
        "             +_:::::::::::::::::::'|*::|~}>     ",
        "             1_::::]]]]]]]]]]]]:::'~|{::|_}%    ",
        "             1_:::::::::::::::::::'..4^'=1+%1   ",
        "             +_::::]]]]]]]]]]]]:::|__])&+%=^%   ",
        "             1_::::::::::::::::::::|#__)&&+'^   ",
        "             1_::::]]]]]]]]]::::::::|#~_])&%^   ",
        "             1_::::::::::::::::::::{||#~_])14   ",
        "             1_::::]]]]]]]]]]]]]]]]]]&}#~_]+4   ",
        "             1_::::::::::::::::::{{{{||#~~@&4   ",
        "             %_::::]]]]]]]]]]]]]]]])))}(~~~&4   ",
        "             %_:::::::::::::::::{{{{{*|#/~_(4   ",
        "             %_::::]]]]]]]]]]]]]]])))))}2;/}4   ",
        "             %_:::::::::::::::{{{{{***||[#~}4   ",
        "             %_::::]]]]]]]]]])]))))))))}2/;)4   ",
        "             %_::::::::::::::{{{{{**|$$[/2~!4   ",
        "             %_::::]]]]]]]]){{{{******$$[2/}4   ",
        "             %_::::::::::::{{{{****$$$$$[2/!4   ",
        "             =_::::]]]]]]])]))))))))})}}[2/!4   ",
        "             %_:::::::::{{{{{{**|$$$$$$[[2;)4   ",
        "             =_::::]]]])]]))))))))))}}}}[22!4   ",
        "             %_::::::::{{{{{|**|$$[$[[[[[22}4   ",
        "             =_::::]]])])))))))))}}}}}}}222-4   ",
        "             =_:::::{{{{{|{*|$$$$$[[[[22222!4   ",
        "             =_::::)]])))))))))}}}}}}(}(2;2-4   ",
        "             =_:::{{{{{{***|$$$$$[[[[22222;-4   ",
        "             =_:::{])))))))))}}}}}}}(}((2;;<4   ",
        "             >_:{{{{{{**|$$$$$[[[[22222;2;;-4   ",
        "             >_{{{{)))))))}}}}}}}(!(((((;;;-4   ",
        "             >_{{{{|**|*$$$$$[[[[22222;;;;;!4   ",
        "             '_{{{{****$$$$$2[[222222;2;;;;-4   ",
        "             '@{{****$$$$$[[[2[222;;2;;;;;;!4   ",
        "             >]{******$$$[$[2[[2222;;;;;;;;!4   ",
        "             '_****$$$$[$[[[[2222;2;;;;;;;;!4   ",
        "             '@__@@@@@@@33<3<<<<<<-<-!!!!!!!4   ",
        "             44444444444444444444444444444444   ",
        "                                                ",
        "                                                ",
        "                                                "]

#------------------------------------------------------------------------
#
# 
#
#------------------------------------------------------------------------
from Plugins import register_report, register_book_item

register_report(
    report,
    _("Comprehensive Ancestors Report"),
    category=_("Text Reports"),
    status=(_("Beta")),
    description= _("Produces a detailed ancestral report."),
    xpm=get_xpm_image(),
    author_name="Tim Waugh",
    author_email="twaugh@redhat.com"
    )

# (name,category,options_dialog,write_book_item,options,style_name,style_file,make_default_style)
register_book_item( 
    _("Comprehensive Ancestors Report"), 
    _("Text"),
    ComprehensiveAncestorsBareReportDialog,
    write_book_item,
    _options,
    _style_name,
    _style_file,
    _make_default_style
   )
